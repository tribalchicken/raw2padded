# raw2padded
**Update:** Experimental functionality to automatically extract relevant dmesg entries. Simply run without an iomem file or physical memory map file.

Automatically convert a raw Linux memory image to a more useful 'padded' image.

This has been designed to work on images captured by LiME in the 'raw' format and convert to the 'padded' format, but it should work with any image which has been acquired by concatenating together the 'System RAM' areas.

The original design motivation was to extract the BIOS-provided physical memory map, but it can also utilise the original /proc/iomem file from the system.

**Note:** Python 3 is required. It has been designed for Python3, but it would not be difficult to convert to something Python2 compatible.

Article here: https://tribalchicken.com.au/dfir/converting-a-memory-image-from-raw-to-padded/ 

### Todo 
* ~~Automatically extract relevant dmesg entries, if present~~ Done!
* Change number base to be consistent (either hex or dec - currently a combination of both is used)
* General code cleanup / fixup

### Usage

```
usage: raw2padded.py [-h] --infile INFILE --outfile OUTFILE
                     [--iomem IOMEMFILE] [--mmap MMAPFILE]

Convert a memory image captured by LiME in raw format to an padded format
image, based on kernel memory mapping information

optional arguments:
  -h, --help            show this help message and exit
  --infile INFILE, -i INFILE
                        raw memory image
  --outfile OUTFILE, -o OUTFILE
                        Padded file to output
  --iomem IOMEMFILE, -m IOMEMFILE
                        Original /proc/iomem file
  --pmap MMAPFILE, -pm PMAPFILE
                        BIOS-provided physical memory map. Refer to README for
                        formatting requirements
```  

### Obtaining the BIOS-provided Physical Memory Map
You can capture this information by using `strings` and grepping for the output. Note that the information may be present in multiple areas of memory and you may get duplication - The tool currently cannot handle this and will give erronous results.

Example:
```
$> strings ram.raw | grep 'BIOS-e820: \['
BIOS-e820: [mem 0x0000000000000000-0x000000000009d7ff] usable
BIOS-e820: [mem 0x000000000009d800-0x000000000009ffff] reserved
BIOS-e820: [mem 0x00000000000e0000-0x00000000000fffff] reserved
BIOS-e820: [mem 0x0000000000100000-0x000000001fffffff] usable
BIOS-e820: [mem 0x0000000020000000-0x00000000201fffff] reserved
BIOS-e820: [mem 0x0000000020200000-0x0000000031498fff] usable
...
```

You can copy this into a file. At this point I would advise against redirecting the output as the tool cannot currently handle multiple/duplicate entries.

You don't need the 'BIOS-e820:' - this will also work:

```
[mem 0x0000000000000000-0x000000000009d7ff] usable
[mem 0x000000000009d800-0x000000000009ffff] reserved
[mem 0x00000000000e0000-0x00000000000fffff] reserved
[mem 0x0000000000100000-0x000000001fffffff] usable
...
```
One entry per line.

### Example

```
overlord@ubnt:~$ python3 raw2padded.py -i ubnt.mem -o ubnt.padded -pm ubnt.mmap
06/15/2016 08:23:15 PM INFO:  Determining new file structure based on provided physical memory map.
06/15/2016 08:23:15 PM DEBUG:  -- Correcting map of first 4096 bytes.
06/15/2016 08:23:15 PM DEBUG:  -- Added 0x9ec00 bytes of file data.
06/15/2016 08:23:15 PM DEBUG:  -- Added 0x400 bytes of padding.
06/15/2016 08:23:15 PM DEBUG:  -- Boundary mismatch. Padding out 0x40000 bytes
06/15/2016 08:23:15 PM DEBUG:  -- Added 0x20000 bytes of padding.
06/15/2016 08:23:15 PM DEBUG:  -- Added 0x3fef0000 bytes of file data.
06/15/2016 08:23:15 PM DEBUG:  -- Added 0xf000 bytes of padding.
06/15/2016 08:23:15 PM DEBUG:  -- Added 0x1000 bytes of padding.
06/15/2016 08:23:15 PM INFO:  Completed building file structure. Estimated output file size is 1073741823 bytes
06/15/2016 08:23:15 PM INFO:  Commencing construction of new file.
06/15/2016 08:23:16 PM DEBUG:  -- Wrote 4096 bytes of padding
06/15/2016 08:23:16 PM DEBUG:  -- Copied 650240 bytes of file data
06/15/2016 08:23:16 PM DEBUG:  -- Wrote 1024 bytes of padding
06/15/2016 08:23:16 PM DEBUG:  -- Wrote 262144 bytes of padding
06/15/2016 08:23:16 PM DEBUG:  -- Wrote 131072 bytes of padding
06/15/2016 08:23:29 PM DEBUG:  -- Copied 1072627712 bytes of file data
06/15/2016 08:23:29 PM INFO:  No more system RAM areas recorded. Skipping any remaining padding.
06/15/2016 08:23:29 PM INFO:  Padded file has been constructed. Happy analysing!
```
