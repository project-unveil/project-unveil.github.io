"""Re-create assets/file/Submission.zip from C:/Users/sihat/Downloads/bones-seed/Submission/."""
import os
import zipfile
from pathlib import Path

SRC_ROOT = Path("C:/Users/sihat/Downloads/bones-seed/Submission")
OUT_ZIP = Path("C:/Users/sihat/Downloads/invert/assets/file/Submission.zip")
SKIP_DIR = "__pycache__"


def should_skip(rel_posix: str) -> bool:
    return SKIP_DIR in rel_posix.split("/") or rel_posix.endswith(".pyc")


def main():
    written = 0
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(SRC_ROOT):
            dirnames[:] = [d for d in dirnames if d != SKIP_DIR]
            for fn in filenames:
                full = Path(dirpath) / fn
                rel = full.relative_to(SRC_ROOT).as_posix()
                if should_skip(rel):
                    continue
                arc = "Submission/" + rel
                z.write(full, arc)
                written += 1
    print(f"Wrote {written} files into {OUT_ZIP}")


if __name__ == "__main__":
    main()
