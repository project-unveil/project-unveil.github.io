"""
Sync the file-browser artefacts from the live submission source.

Reads SOURCE_DIR and rewrites:
  - code/src/         — the file-browser source tree
  - code/manifest.json — the file-browser manifest

The downloadable zip is **not** produced here. It is built in the visitor's
browser at click time from these same files, so this script just keeps
code/src/ + manifest.json in sync with the live source.

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
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

# Live source tree (the canonical copy on the author's machine).
DEFAULT_SOURCE = Path("C:/Users/sihat/Downloads/bones-seed/Submission")

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


def sync_src(source: Path) -> int:
    """Copy the live source tree into code/src/, skipping cache files."""
    wipe(SRC_DIR)
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = [d for d in dirnames if d != SKIP_DIR]
        for fn in filenames:
            full = Path(dirpath) / fn
            rel = full.relative_to(source).as_posix()
            if should_skip(rel):
                continue
            dst = SRC_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
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

    count = sync_src(source)
    manifest = write_manifest()

    print(f"Source     : {source}")
    print(f"Src tree   : {SRC_DIR.relative_to(REPO_ROOT)}  ({count} files)")
    print(f"Manifest   : {MANIFEST_PATH.relative_to(REPO_ROOT)}  "
          f"({len(manifest['tree'])} top-level entries)")
    print("Note       : the downloadable zip is built client-side at click time.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
