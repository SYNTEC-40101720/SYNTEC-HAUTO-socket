import tokenize, io

tests = [
    (b'# UTF-8\nVSVersionInfo(...)\n', 'bare "# UTF-8" (NOT valid PEP263)'),
    (b'# -*- coding: utf-8 -*-\nVSVersionInfo(...)\n', '"# -*- coding: utf-8 -*-"'),
    (b'# coding: cp1252\nVSVersionInfo(...)\n', '"# coding: cp1252"'),
    (b'no header\nVSVersionInfo(...)\n', 'no header at all'),
]
for data, desc in tests:
    enc, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    print(f'{desc:>50s} -> {enc}')
