from pathlib import Path

root = Path('src')
for p in sorted(root.rglob('*.py')):
    for i, line in enumerate(p.read_text(encoding='utf-8').splitlines(), start=1):
        if len(line) > 88:
            print(f"{p}:{i}:{len(line)}")
