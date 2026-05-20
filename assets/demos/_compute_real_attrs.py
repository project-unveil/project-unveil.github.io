"""Adhoc: print real-metadata GT + delta-preserved pred for every demo.
Not committed — discarded after the DEMOS rewrite.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("BONES_SEED_DIR", r"C:\Users\sihat\Downloads\bones-seed")
os.environ.setdefault("BVH2SMPL_SRC",   r"C:\Users\sihat\Downloads\BVH2SMPL\src")

from generate_all_demos import DEMOS
import pandas as pd

df = pd.read_parquet(
    r"C:\Users\sihat\Downloads\bones-seed\metadata\seed_metadata_v003.parquet",
    columns=["filename","actor_height_cm","actor_weight_kg","actor_gender","actor_age_yr"],
)

g_map = {"M": "male", "F": "female"}
print(f"{'id':<13} {'real_gt (h,w,a,g)':<28} {'delta (h,w,a)':<14} {'new_pred (h,w,a,g)':<28}")
print("-" * 85)
for d in DEMOS:
    stem = os.path.splitext(os.path.basename(d["bvh"]))[0]
    r = df[df["filename"] == stem]
    if r.empty:
        print(f"{d['id']:<13} NO METADATA — stem={stem}")
        continue
    rr = r.iloc[0]
    real_g = g_map.get(str(rr.actor_gender).strip().upper(),
                       str(rr.actor_gender).lower())
    real_gt = (int(rr.actor_height_cm), int(rr.actor_weight_kg),
               int(rr.actor_age_yr), real_g)
    old_gt = (d["gt"]["height"], d["gt"]["weight"],
              d["gt"]["age"],   d["gt"]["gender"])
    old_pr = (d["pred"]["height"], d["pred"]["weight"],
              d["pred"]["age"],   d["pred"]["gender"])
    dh = old_pr[0] - old_gt[0]
    dw = old_pr[1] - old_gt[1]
    da = old_pr[2] - old_gt[2]
    new_pr = (real_gt[0] + dh, real_gt[1] + dw, real_gt[2] + da, real_g)
    print(f"{d['id']:<13} {str(real_gt):<28} ({dh:+d},{dw:+d},{da:+d})    "
          f"   {str(new_pr):<28}")
