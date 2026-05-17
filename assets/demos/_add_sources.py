"""One-off: backfill sourceG1Csv + sourceBvh into demos_config.json by
reading the DEMOS dict in generate_all_demos.py and computing relative
paths against BONES_SEED. Inserts the fields right after smplFacesFile.
"""
import json, os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
CFG  = os.path.join(HERE, "demos_config.json")
GEN  = os.path.join(HERE, "generate_all_demos.py")

# Stub the env vars so generate_all_demos can be imported without a real
# bones-seed dir; we only need the DEMOS list.
os.environ.setdefault("BONES_SEED_DIR", "/_stub_bones_seed_")
os.environ.setdefault("BVH2SMPL_SRC",   "/_stub_bvh2smpl_/src")

spec = importlib.util.spec_from_file_location("gen", GEN)
gen  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

# Map id -> (g1 rel, bvh rel) using gen.BONES_SEED as the root
SOURCES = {}
for d in gen.DEMOS:
    did = d["id"]
    g1  = os.path.relpath(d["g1"],  gen.BONES_SEED).replace("\\", "/")
    bvh = os.path.relpath(d["bvh"], gen.BONES_SEED).replace("\\", "/")
    SOURCES[did] = (g1, bvh)

with open(CFG, "r", encoding="utf-8") as f:
    cfg = json.load(f)

missing = []
for d in cfg["demos"]:
    did = d["id"]
    if did not in SOURCES:
        missing.append(did)
        continue
    g1_src, bvh_src = SOURCES[did]
    ordered = {}
    for k in ("id", "label", "count",
              "g1CsvFile", "smplPredFile", "smplGtFile", "smplFacesFile"):
        if k in d: ordered[k] = d[k]
    ordered["sourceG1Csv"] = g1_src
    ordered["sourceBvh"]   = bvh_src
    for k in ("numFrames", "fps", "predicted", "groundTruth"):
        if k in d: ordered[k] = d[k]
    for k, v in d.items():
        if k not in ordered: ordered[k] = v
    d.clear()
    d.update(ordered)

with open(CFG, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")

if missing:
    print(f"WARN: no source mapping for: {missing}", file=sys.stderr)
print(f"Updated {len(cfg['demos'])} demos.")
