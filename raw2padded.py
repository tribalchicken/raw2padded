#!/usr/bin/python
"""
Convert a memory image captured by LiME in raw format to an padded format image, based on kernel memory mapping information

@author Thomas White
@contact thomas@tribalchicken.com.au
@license: Beer-ware
"""

import argparse
import re
import logging

# Max number of bytes to allocate to one single pad or copy operation
# Avoids running out of VA space when encountering an unexpectedly-large mem range
COPY_LIMIT = 1073741824 

parser = argparse.ArgumentParser(description="Convert a memory image captured by LiME in raw format to an padded format image, based on kernel memory mapping information")
parser.add_argument('--infile', '-i', dest='infile', help='raw memory image', required=True)
parser.add_argument('--outfile', '-o', dest='outfile', help='Padded file to output', required=True)
parser.add_argument('--iomem','-m',dest='iomemfile', help='Original /proc/iomem file', required=False)
parser.add_argument('--pmap','-pm',dest='pmapfile', help='BIOS-provided physical memory map. Refer to README for formatting requirements', required=False)

args = parser.parse_args()
logging.basicConfig(format='%(asctime)s %(levelname)s:  %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)

def createOutputStructure(input):
    """ Read the provided memory mapping file and create a list containing the type and length of a file section"""
    
    logging.info("Determining new file structure based on provided physical memory map.")
    newFileStruct = []
    # Identifying the range end - 1 helps to identify range gaps.
    lastEnd = 0
    # Keep track of the number of system RAM entries. This enables us to avoid unnecessary padding at the end of the file
    sysEntries = 0
    
    for index,i in enumerate(input):
        if "mem" in input[0]:
            #RE to Extract memory range and type
            p = re.compile("(0[xX][0-9a-fA-F]+)-(0[xX][0-9a-fA-F]+)]\s(.+)")
        elif args.iomemfile:
            if (i[:1] == " "):
                logging.debug("-- Skipping nested iomem line.")
                continue
            p = re.compile("([0-9a-fA-F]+)-([0-9a-fA-F]+)\s:\s(.+)") # iomem is a different format
        else:
            logging.critical("-- Fatal error encountered whilst preparing to create file structure. Unable to extract required information. Exiting, sorry :(")
            exit(1)            
        memRange = p.search(i)
        if memRange:
            rangeStart = int(memRange.group(1), 16)
            rangeEnd = int(memRange.group(2), 16)
            rangeType = memRange.group(3).strip('\x00')

            # Add to structure. 
            # just want the length and type
            if ((rangeType == 'usable') or (rangeType == 'System RAM')):
                memType = 1
                sysEntries = sysEntries + 1
            else:
                memType = 0

            # if the distance from the last entry is greater than 1, then we need to pad that out first
            if len(newFileStruct):
                mapHole = rangeStart - lastEnd
                if mapHole > 1:
                    logging.debug("-- Boundary mismatch. Padding out %s bytes", str(hex(mapHole-1)))
                    while (mapHole > 1073741824):
                        logging.debug("-- Requested padding size is excessive. Splitting into 1GB pieces. Note this will modify the apparent layout.")
                        newFileStruct.append([0,COPY_LIMIT])
                        mapHole = mapHole - COPY_LIMIT
                    newFileStruct.append([0,mapHole-1])
            if index == 0:
                # Check if the first range is 0x0 to 0xFFF
                # As far as I'm aware linux always reserves the first 0xFFF bytes (Usually physical mem map is updated after rcvd from BIOS)
                # If someone more knowledgable reads this and I am wrong, please correct me :)
                if ((rangeStart == 0) and (rangeEnd != 4095)): 
                    logging.debug("-- Correcting map of first 4096 bytes.")
                    newFileStruct.append([0,4096])
                    rangeStart = 4096
                    
            
            # Save end of range for later
            lastEnd = int(memRange.group(2),16)
            wrBytes = rangeEnd - rangeStart    
            while (wrBytes > COPY_LIMIT):
                        logging.debug("-- Requested copy size is excessive. Splitting into 1GB pieces. Note this will modify the apparent layout.")
                        newFileStruct.append([1,COPY_LIMIT])
                        wrBytes = wrBytes - COPY_LIMIT  
            logging.debug("-- Added %s bytes of %s.", str(hex(wrBytes+1)), "file data" if memType == 1 else "padding")
            newFileStruct.append([memType,wrBytes+1])
        else:
            logging.critical("-- Fatal error encountered whilst preparing to create file structure. Unable to extract required information. Exiting, sorry :(")
            exit(1)  
    logging.info("Completed building file structure. Estimated output file size is %s bytes", str(lastEnd))
    return newFileStruct, sysEntries
                
def buildFile(input, output, fileStruct, sysEntries):
    """ 
    Use the calculated file structure top create a padded file.
    Generate sections of padding and write to the file. Data sections will be copied from the input file.    
    """
     
    logging.info("Commencing construction of new file.")
    oFile = open(output, 'wb')
    iFile = open(input, 'rb')
    
    if not oFile:
        logging.critical("-- Error opening output file")
        exit(1)
    if not iFile:
        logging.critical("-- Error opening input file")
        exit(1)
    
    for entry in fileStruct:
        if sysEntries == 0:
            logging.info("No more system RAM areas recorded. Skipping any remaining padding.")
            break;
    
        if entry[0] == 0:
            
            padBytes = bytearray(b'\0' * entry[1]) # Padding
                    
            written = oFile.write(padBytes)
            
            # Validate - only works on py 3
            if written != entry[1]:
               logging.warning("-- PADDING: Write validation error! Bytes written does not match requested length. Req %s Wr %s",str(entry[1]), str(written))
            else:
               logging.debug("-- Wrote %s bytes of padding", str(written))
        if entry[0] == 1:
            c = iFile.read(entry[1])
            if c:
                written = oFile.write(c)
                # Validate - only works on py 3
                if written != entry[1]:
                  logging.warning("-- COPY: Write validation error! Bytes written does not match requested length. Req %s Wr %s",str(entry[1]), str(written))
                else:
                  logging.debug("-- Copied %s bytes of file data", str(written))
            else:
                logging.critical("-- Failed to get necassary bytes from input file")
            sysEntries = sysEntries - 1
    logging.info("Padded file has been constructed. Happy analysing!")

if args.pmapfile is not None:
    with open(args.mmapfile,'r') as f:
        mmap = f.readlines()
        newFileStruct, sysEntries = createOutputStructure(mmap)
        buildFile(args.infile, args.outfile, newFileStruct, sysEntries)

# Can these be combined into one?
if args.iomemfile is not None:
    with open(args.iomemfile,'r') as f:
        iomem = f.readlines()
        newFileStruct, sysEntries = createOutputStructure(iomem)
        buildFile(args.infile, args.outfile, newFileStruct, sysEntries)