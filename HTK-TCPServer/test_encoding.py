# Test encoding of version_info.txt
import tokenize
import io
import re

# Test the actual version_info.txt file
with open(r'd:\FN\华途\HTK-TCPServer\version_info.txt', 'rb') as f:
    raw = f.read()

print('=== File size ===', len(raw), 'bytes')
print()

# Test tokenize.detect_encoding on the actual file
with open(r'd:\FN\华途\HTK-TCPServer\version_info.txt', 'rb') as f:
    encoding, _ = tokenize.detect_encoding(f.readline)
    print('Tokenize detected encoding:', encoding)
print()

# Print first 2 lines raw
lines = raw.split(b'\n')
print('Line 1 raw:', lines[0][:60])
print('Line 2 raw:', lines[1][:60] if len(lines) > 1 else 'N/A')
print()

# Decode using misc (same as PyInstaller does)
from PyInstaller.utils import misc
decoded = misc.decode(raw)
print('Decoded successfully, length:', len(decoded))
print()

# Find the Chinese characters in decoded text
chinese = re.findall(r'[\u4e00-\u9fff]+', decoded)
print('Chinese chars found:', chinese)
print()

# Properly parse using the VSVersionInfo approach
from PyInstaller.utils.win32 import versioninfo as vi
info = vi.load_version_info_from_text_file(r'd:\FN\华途\HTK-TCPServer\version_info.txt')
print('=== VSVersionInfo loaded successfully ===')
print('CompanyName:', repr(info.kids[0].kids[0].kids[0].val))
print('FileDescription:', repr(info.kids[0].kids[0].kids[1].val))
print('FileVersion:', repr(info.kids[0].kids[0].kids[2].val))
print('ProductName:', repr(info.kids[0].kids[0].kids[3].val))
print('ProductVersion:', repr(info.kids[0].kids[0].kids[4].val))
print('LegalCopyright:', repr(info.kids[0].kids[0].kids[5].val))
print()

# Test serialization
raw_bytes = info.toRaw()
print('Serialized bytes length:', len(raw_bytes))
print()

# Check StringTable name
st = info.kids[0].kids[0]
print('StringTable name:', repr(st.name))
print()

# Check VarFileInfo
vf = info.kids[1]
print('VarFileInfo kids:', vf.kids)
if hasattr(vf.kids[0], 'val'):
    print('Translation value:', vf.kids[0].val)
print()

# Test round-trip: serialize → deserialize
print('=== Round-trip test ===')
rt = vi.VSVersionInfo.fromRaw(raw_bytes, 0, len(raw_bytes))
print('Round-trip FileDescription:', repr(rt.kids[0].kids[0].kids[1].val))
