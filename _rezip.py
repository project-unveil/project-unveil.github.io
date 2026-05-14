import os, zipfile
from pathlib import Path
SRC = Path("C:/Users/sihat/Downloads/bones-seed/Submission")
OUT = Path("C:/Users/sihat/Downloads/invert/assets/file/Submission.zip")
SKIP = "__pycache__"
written = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for dirpath, dirnames, filenames in os.walk(SRC):
        dirnames[:] = [d for d in dirnames if d != SKIP]
        for fn in filenames:
            full = Path(dirpath) / fn
            rel = full.relative_to(SRC).as_posix()
            if SKIP in rel.split("/") or rel.endswith(".pyc"):
                continue
            z.write(full, "Submission/" + rel)
            written += 1
print(f"Wrote {written} files into {OUT}")
