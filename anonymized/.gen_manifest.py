"""
Build anonymized/manifest.json from the local g1_sanitized_pmr_contrast_full
source directory. Output is grouped by date dir for compactness:

  {
    "210531": ["file1.csv", "file2.csv", ...],
    "210707": [...]
  }

Total file paths reconstructed client-side as "csv/<date>/<file>".
"""
import json
import os
import sys

ROOT = r"C:\Users\sihat\Downloads\bones-seed\g1_sanitized_pmr_contrast_full\g1\csv"
OUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json")


def main() -> int:
    if not os.path.isdir(ROOT):
        sys.exit(f"Source dir not found: {ROOT}")
    out: dict[str, list[str]] = {}
    for d in sorted(os.listdir(ROOT)):
        sub = os.path.join(ROOT, d)
        if not os.path.isdir(sub):
            continue
        files = sorted(f for f in os.listdir(sub) if f.endswith(".csv"))
        if files:
            out[d] = files
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    total = sum(len(v) for v in out.values())
    size_kb = os.path.getsize(OUT) / 1024
    print(f"Wrote {total} files across {len(out)} dirs -> {OUT} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
