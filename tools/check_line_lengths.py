from pathlib import Path
p = Path('src/subtitle_ocr_gui/app.py')
for i, line in enumerate(p.read_text(encoding='utf-8').splitlines(), start=1):
    if len(line) > 88:
        print(i, len(line), repr(line))
