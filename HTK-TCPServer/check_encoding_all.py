"""检查所有文件的编码问题"""
import os
import re

base = r'd:\FN\华途'

# 1. Check spec files for version parameter
print("=== Spec file version check ===")
spec_files = [
    r'd:\FN\华途\HTK-TCPServer\SYNTEC-HTK-TCPServer.spec',
    r'd:\FN\华途\HTK-TCPServer\SYNTEC-示教器TCP服务端.spec',
]
for path in spec_files:
    name = os.path.basename(path)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'version=' in content:
        m = re.search(r"version\s*=\s*'([^']+)'", content)
        if m:
            print(f'  {name}: version file = {m.group(1)}')
        else:
            print(f'  {name}: has version= but unrecognized format')
    else:
        print(f'  {name}: NO version= (no version info!)')

print()

# 2. Check all .py files for encoding issues
print("=== Python file encoding check ===")
errors = []
for root, dirs, files in os.walk(base):
    # Skip build and dist directories
    if 'build' in root or 'dist' in root or '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'rb') as fh:
                    raw = fh.read()
                raw.decode('utf-8')
            except UnicodeDecodeError:
                errors.append(path)
                try:
                    raw.decode('gbk')
                    print(f'  GBK ENCODED: {path}')
                except:
                    print(f'  UNKNOWN ENCODING: {path}')

if not errors:
    print('  All Python files are valid UTF-8 ✅')
print()

# 3. Check .spec and .txt files for encoding
print("=== .spec / .txt / .json / .ini encoding check ===")
extensions = ['.spec', '.txt', '.json', '.ini', '.md']
for root, dirs, files in os.walk(base):
    if 'build' in root or 'dist' in root or '__pycache__' in root:
        continue
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in extensions:
            path = os.path.join(root, f)
            try:
                with open(path, 'rb') as fh:
                    raw = fh.read()
                raw.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    gbk_text = raw.decode('gbk')
                    if any(ord(c) > 127 for c in gbk_text):
                        print(f'  GBK ENCODED: {path}')
                except:
                    print(f'  UNKNOWN ENCODING: {path}')

print()
print("=== Checking exe name Chinese chars ===")
spec1 = r'd:\FN\华途\HTK-TCPServer\SYNTEC-HTK-TCPServer.spec'
with open(spec1, 'r', encoding='utf-8') as f:
    content = f.read()
m = re.search(r"name\s*=\s*'([^']+)'", content)
if m:
    print(f'  SYNTEC-HTK-TCPServer.spec: name = {m.group(1)}')

spec2 = r'd:\FN\华途\HTK-TCPServer\SYNTEC-示教器TCP服务端.spec'
with open(spec2, 'r', encoding='utf-8') as f:
    content = f.read()
m = re.search(r"name\s*=\s*'([^']+)'", content)
if m:
    print(f'  SYNTEC-示教器TCP服务端.spec: name = {m.group(1)}')

print()
print("=== version_info.txt Chinese hex check ===")
with open(r'd:\FN\华途\HTK-TCPServer\version_info.txt', 'rb') as f:
    raw = f.read()

# Show bytes around '示教器'
idx = raw.find(b'\xe7\xa4\xba\xe6\x95\x99\xe5\x99\xa8')
if idx >= 0:
    print(f'示教器 at byte offset {idx}')
    print(f'Hex: {raw[idx-5:idx+25].hex(" ")}')
    context = raw[max(0,idx-10):idx+35].decode('utf-8', errors='replace')
    print(f'Context: ...{context}...')

idx = raw.find(b'\xe6\xa8\xa1\xe6\x8b\x9f\xe7\xab\xaf')
if idx >= 0:
    print(f'模拟端 at byte offset {idx}')
    print(f'Hex: {raw[idx-5:idx+20].hex(" ")}')
    
# Check copyright symbol
idx = raw.find(b'\xc2\xa9')
if idx >= 0:
    print(f'© symbol at byte offset {idx}')
    print(f'Hex: {raw[max(0,idx-2):idx+6].hex(" ")}')
    # Also check for bare \xa9 (latin-1 encoding of ©)
idx2 = raw.find(b'\xa9')
if idx2 >= 0 and idx2 != raw.find(b'\xc2\xa9'):
    print(f'WARNING: bare \\xa9 found at offset {idx2} (could be Latin-1/GBK encoded ©)')
