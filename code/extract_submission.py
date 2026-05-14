"""
Build the live submission artefacts.

Reads the source tree at SOURCE_DIR, then in a single pass:
  1. (re)builds  assets/file/Submission.zip       — the downloadable bundle
  2. (re)writes  code/src/                        — the file-browser source tree
  3. (re)writes  code/manifest.json               — the file-browser manifest

`code/src/` and `Submission.zip` are derived artefacts of SOURCE_DIR; do not edit
them by hand — edit the live source and re-run this script.

Skips __pycache__/ directories and *.pyc files.

Run from the repo root or from code/:
    python code/extract_submission.py
    python code/extract_submission.py --source D:/path/to/Submission
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

# Live source tree (the canonical copy on the author's machine).
DEFAULT_SOURCE = Path("C:/Users/sihat/Downloads/bones-seed/Submission")

ZIP_PATH = REPO_ROOT / "assets" / "file" / "Submission.zip"
SRC_DIR = HERE / "src"
MANIFEST_PATH = HERE / "manifest.json"

SKIP_DIR = "__pycache__"

LANG_BY_EXT = {
    ".py": "python",
    ".md": "markdown",
    ".txt": "plaintext",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sh": "bash",
    ".cfg": "ini",
    ".ini": "ini",
    ".toml": "toml",
}


def should_skip(rel_posix: str) -> bool:
    if SKIP_DIR in rel_posix.split("/"):
        return True
    if rel_posix.endswith(".pyc"):
        return True
    return False


def infer_lang(path: Path) -> str:
    return LANG_BY_EXT.get(path.suffix.lower(), "plaintext")


def wipe(path: Path) -> None:
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def iter_source_files(source: Path):
    """Yield (full_path, posix_rel_path) for every non-skipped file under
    SOURCE."""
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = [d for d in dirnames if d != SKIP_DIR]
        for fn in filenames:
            full = Path(dirpath) / fn
            rel = full.relative_to(source).as_posix()
            if should_skip(rel):
                continue
            yield full, rel


def build_artefacts(source: Path) -> int:
    """Copy live source → code/src/ and write Submission.zip in one pass."""
    wipe(SRC_DIR)
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in iter_source_files(source):
            # Mirror under code/src/ (paths relative to the submission root).
            dst = SRC_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
            # And inside the zip with the conventional "Submission/" prefix.
            zf.write(full, "Submission/" + rel)
            count += 1
    return count


def build_tree(root: Path):
    """Recursively build the nested dict/list manifest from code/src/."""
    entries = []
    for child in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        rel = child.relative_to(SRC_DIR).as_posix()
        if child.is_dir():
            entries.append({
                "type": "dir",
                "name": child.name,
                "path": rel,
                "children": build_tree(child),
            })
        else:
            entries.append({
                "type": "file",
                "name": child.name,
                "path": rel,
                "size": child.stat().st_size,
                "lang": infer_lang(child),
            })
    return entries


def write_manifest() -> dict:
    manifest = {
        "root": "Submission",
        "default_file": "README.md",
        "tree": build_tree(SRC_DIR),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                   help=f"Live submission source directory (default: {DEFAULT_SOURCE})")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source: Path = args.source

    if not source.is_dir():
        print(f"ERROR: source directory not found: {source}", file=sys.stderr)
        print("       pass --source <path> if the live tree lives elsewhere.",
              file=sys.stderr)
        return 1

    count = build_artefacts(source)
    manifest = write_manifest()
    zip_size = ZIP_PATH.stat().st_size

    print(f"Source     : {source}")
    print(f"Zip        : {ZIP_PATH.relative_to(REPO_ROOT)}  ({zip_size:,} bytes)")
    print(f"Src tree   : {SRC_DIR.relative_to(REPO_ROOT)}  ({count} files)")
    print(f"Manifest   : {MANIFEST_PATH.relative_to(REPO_ROOT)}  "
          f"({len(manifest['tree'])} top-level entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
