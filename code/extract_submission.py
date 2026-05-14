"""
Extract assets/file/Submission.zip into code/src/ and emit code/manifest.json.

Skips __pycache__/ directories and *.pyc files. Strips the leading "Submission/"
prefix from paths so code/src/ holds the contents of the submission directly.

Re-runnable: wipes code/src/ and code/manifest.json before regenerating.

Run from the repo root or from code/:
    python code/extract_submission.py
"""

import json
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
ZIP_PATH = REPO_ROOT / "assets" / "file" / "Submission.zip"
SRC_DIR = HERE / "src"
MANIFEST_PATH = HERE / "manifest.json"

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


def should_skip(member_name: str) -> bool:
    parts = member_name.split("/")
    if any(p == "__pycache__" for p in parts):
        return True
    if member_name.endswith(".pyc"):
        return True
    return False


def strip_root(member_name: str) -> str:
    # Drop the leading "Submission/" so SRC_DIR holds the contents directly.
    prefix = "Submission/"
    if member_name.startswith(prefix):
        return member_name[len(prefix):]
    return member_name


def infer_lang(path: Path) -> str:
    return LANG_BY_EXT.get(path.suffix.lower(), "plaintext")


def wipe_src():
    if SRC_DIR.exists():
        shutil.rmtree(SRC_DIR)
    SRC_DIR.mkdir(parents=True, exist_ok=True)


def extract():
    if not ZIP_PATH.exists():
        raise SystemExit(f"Submission zip not found at {ZIP_PATH}")

    wipe_src()
    extracted_files = 0
    with zipfile.ZipFile(ZIP_PATH) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            if should_skip(info.filename):
                continue
            rel = strip_root(info.filename)
            if not rel:
                continue
            out_path = SRC_DIR / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted_files += 1
    return extracted_files


def build_tree(root: Path):
    """Build a nested dict/list manifest from the extracted src/ tree."""
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


def write_manifest():
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


def main():
    n = extract()
    manifest = write_manifest()
    file_count = sum(1 for _ in SRC_DIR.rglob("*") if _.is_file())
    print(f"Extracted {n} entries from {ZIP_PATH.name}")
    print(f"Wrote {file_count} files into {SRC_DIR.relative_to(REPO_ROOT)}")
    print(f"Wrote manifest to {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"Top-level entries: {len(manifest['tree'])}")


if __name__ == "__main__":
    main()
