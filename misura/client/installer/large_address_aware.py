# See http://en.wikibooks.org/wiki/X86_Disassembly/Windows_Executable_Files#PE_Header
# and https://msdn.microsoft.com/en-us/library/ms680349%28v=vs.85%29.aspx

exe = '.\\dist\\misura4\\misura.exe'
exe = 'C:\\Program Files (x86)\\Misura\\misura.exe'

import struct

IMAGE_FILE_LARGE_ADDRESS_AWARE = 0x0020
PE_HEADER_OFFSET = 60
CHARACTERISTICS_OFFSET = 18

def set_large_address_aware(filename):
    f = open(filename, 'rb+')
    # Check for MZ Header
    if f.read(2) != b'MZ':
        print('Not MZ')
        return False
    # Get PE header location
    f.seek(PE_HEADER_OFFSET)
    pe_header_loc, = struct.unpack('i', f.read(4))
    # Get PE header, check it
    f.seek(pe_header_loc)
    if f.read(4) != b'PE\0\0':
        print('error in PE header')
        return False
    # Get Characteristics, check if IMAGE_FILE_LARGE_ADDRESS_AWARE bit is set
    charac_offset = pe_header_loc + 4 + CHARACTERISTICS_OFFSET
    f.seek(charac_offset)
    bits, = struct.unpack('h', f.read(2))
    if (bits & IMAGE_FILE_LARGE_ADDRESS_AWARE) == IMAGE_FILE_LARGE_ADDRESS_AWARE:
        return True
    else:
        print('large_address_aware is NOT set - will try to set')
        f.seek(charac_offset)
        bytes = struct.pack('h', (bits | IMAGE_FILE_LARGE_ADDRESS_AWARE))
        f.write(bytes)
    f.close()
    return False

 
if set_large_address_aware(exe):
    print('large_address_aware is set')
else:
    print('large_address_aware was NOT set')