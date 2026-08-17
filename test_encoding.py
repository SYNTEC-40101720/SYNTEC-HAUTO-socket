import tokenize
import io

# Test what tokenize.detect_encoding does with '# UTF-8' (NOT a valid PEP263 cookie)
test1 = b'# UTF-8\nVSVersionInfo(...)\n'
enc1, _ = tokenize.detect_encoding(io.BytesIO(test1).readline)
print('1) With bare "# UTF-8" (NOT valid PEP263 cookie):', repr(enc1))

# Test with valid encoding cookie
test2 = b'# -*- coding: utf-8 -*-\nVSVersionInfo(...)\n'
enc2, _ = tokenize.detect_encoding(io.BytesIO(test2).readline)
print('2) With "# -*- coding: utf-8 -*-":', repr(enc2))

# Test with cp1252 encoding cookie
test3 = b'# coding: cp1252\nVSVersionInfo(...)\n'
enc3, _ = tokenize.detect_encoding(io.BytesIO(test3).readline)
print('3) With "# coding: cp1252":', repr(enc3))

# Test GBK content (0xb2e2 = 测, 0xcad4 = 试) without any cookie
test4 = b'# UTF-8\nVSVersionInfo(\n  kids=[StringStruct("FileDescription", "\xb2\xe2\xca\xd4")]\n)'
enc4, _ = tokenize.detect_encoding(io.BytesIO(test4).readline)
print('4) GBK Chinese, bare "# UTF-8":', repr(enc4))

# Test what Python's default is
test5 = b'Something without encoding header\n'
enc5, _ = tokenize.detect_encoding(io.BytesIO(test5).readline)
print('5) No encoding info at all:', repr(enc5))
