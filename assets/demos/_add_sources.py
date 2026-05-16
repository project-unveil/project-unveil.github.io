"""One-off: add `sourceG1Csv` and `sourceBvh` (relative to bones-seed root)
to each entry in demos_config.json. Run once, then delete."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG  = os.path.join(HERE, "demos_config.json")

SOURCES = {
    "walking":      ("g1/csv/240918/grab_walk_ff_180_001__A548.csv",       "soma_uniform/bvh/240918/grab_walk_ff_180_001__A548.bvh"),
    "jogging":      ("g1/csv/240918/smoke_jog_ff_360_stop_R_001__A548.csv","soma_uniform/bvh/240918/smoke_jog_ff_360_stop_R_001__A548.bvh"),
    "gesture":      ("g1/csv/240529/neutral_alone_R_001__A542.csv",        "soma_uniform/bvh/240529/neutral_alone_R_001__A542.bvh"),
    "action":       ("g1/csv/240529/neutral_itching_head_R_001__A542.csv", "soma_uniform/bvh/240529/neutral_itching_head_R_001__A542.bvh"),
    "dancing":      ("g1/csv/240529/macarena_001__A545_M.csv",             "soma_uniform/bvh/240529/macarena_001__A545_M.bvh"),
    "jumping":      ("g1/csv/240527/neutral_dancecard_jump_002__A534.csv", "soma_uniform/bvh/240527/neutral_dancecard_jump_002__A534.bvh"),
    "turning":      ("g1/csv/240918/idle_turn_000_R_long_002__A548.csv",   "soma_uniform/bvh/240918/idle_turn_000_R_long_002__A548.bvh"),
    "climbing_box": ("g1/csv/240529/neutral_come_down_50cm_box_R_001__A542.csv", "soma_uniform/bvh/240529/neutral_come_down_50cm_box_R_001__A542.bvh"),
    "kneeling":     ("g1/csv/230713/knightly_bow_R_001__A429.csv",         "soma_uniform/bvh/230713/knightly_bow_R_001__A429.bvh"),
    "exercising":   ("g1/csv/231019/squeak_003__A484.csv",                 "soma_uniform/bvh/231019/squeak_003__A484.bvh"),
    "pulling":      ("g1/csv/231019/high_big_crank_ccw_002__A484.csv",     "soma_uniform/bvh/231019/high_big_crank_ccw_002__A484.bvh"),
    "throwing":     ("g1/csv/230424/throw_ball_R_001__A345.csv",           "soma_uniform/bvh/230424/throw_ball_R_001__A345.bvh"),
    "guitar":       ("g1/csv/230417/playing_guitar_R_001__A330.csv",       "soma_uniform/bvh/230417/playing_guitar_R_001__A330.bvh"),
}

with open(CFG, "r", encoding="utf-8") as f:
    cfg = json.load(f)

# Reorder keys per entry so source fields land right after smplFacesFile,
# before the binary metadata (numFrames/fps/predicted/groundTruth).
new_demos = []
missing = []
for d in cfg["demos"]:
    did = d["id"]
    if did not in SOURCES:
        missing.append(did)
        new_demos.append(d)
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
    # Preserve any other unknown keys at the end
    for k, v in d.items():
        if k not in ordered: ordered[k] = v
    new_demos.append(ordered)

cfg["demos"] = new_demos
with open(CFG, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")

if missing:
    print(f"WARN: no source mapping for: {missing}", file=sys.stderr)
print(f"Updated {len(cfg['demos'])} demos.")
