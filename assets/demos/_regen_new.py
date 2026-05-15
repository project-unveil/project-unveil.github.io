"""One-off: regen smoking + guitar binaries, copy their G1 CSVs, and print
numFrames/fps for paste into demos_config.json.
"""
import os, sys, struct, shutil
import numpy as np

HERE         = os.path.dirname(os.path.abspath(__file__))
BONES_SEED   = os.environ.get("BONES_SEED_DIR", r"C:\Users\sihat\Downloads\bones-seed")
BVH2SMPL_SRC = os.environ.get("BVH2SMPL_SRC",   r"C:\Users\sihat\Downloads\BVH2SMPL\src")
SMPL_DIR     = os.path.join(BVH2SMPL_SRC, "rendering_utils", "smpl")
SMPL_MODELS  = {
    "male":   os.path.join(SMPL_DIR, "basicmodel_m_lbs_10_207_0_v1.0.0.pkl"),
    "female": os.path.join(SMPL_DIR, "basicModel_f_lbs_10_207_0_v1.0.0.pkl"),
}
G1_OUT       = os.path.join(HERE, "g1_csv")
SMPL_OUT     = os.path.join(HERE, "smpl")
MAX_FRAMES   = 150

JOBS = [
    dict(id="smoking",
         g1 =os.path.join(BONES_SEED, r"g1\csv\240918\idle_to_smoke_idle_R_001__A549.csv"),
         bvh=os.path.join(BONES_SEED, r"soma_uniform\bvh\240918\idle_to_smoke_idle_R_001__A549.bvh"),
         pred=dict(height=169, weight=73, gender="male"),
         gt  =dict(height=172, weight=70, gender="male")),
    dict(id="guitar",
         g1 =os.path.join(BONES_SEED, r"g1\csv\230417\playing_guitar_R_001__A330.csv"),
         bvh=os.path.join(BONES_SEED, r"soma_uniform\bvh\230417\playing_guitar_R_001__A330.bvh"),
         pred=dict(height=172, weight=58, gender="female"),
         gt  =dict(height=169, weight=61, gender="female")),
]


def save_verts(verts, fps, path):
    nf, nv, _ = verts.shape
    with open(path, "wb") as f:
        f.write(struct.pack("<II", nf, nv))
        f.write(struct.pack("<f", float(fps)))
        f.write(verts.astype(np.float32).ravel().tobytes())
    print(f"  -> {os.path.basename(path)}  ({nf}fr, fps={fps:.4f}, {os.path.getsize(path)/1e6:.1f}MB)")


def run_smpl(bvh_path, height, weight, gender):
    sys.path.insert(0, BVH2SMPL_SRC)
    os.chdir(BVH2SMPL_SRC)
    from soma_viewer import BVHMotionZYX, fit_smpl
    bvh = BVHMotionZYX(os.path.abspath(bvh_path))
    nf = bvh.motion_length
    verts, _ = fit_smpl(
        bvh, scale=100.0,
        smpl_path=SMPL_MODELS[gender], device="cpu",
        height_cm=height, weight_kg=weight, gender=gender,
    )
    if nf > MAX_FRAMES:
        idx = np.round(np.linspace(0, nf-1, MAX_FRAMES)).astype(int)
        verts = verts[idx]
        eff_fps = 120.0 * MAX_FRAMES / nf
    else:
        eff_fps = 120.0
    return verts, eff_fps


def main():
    summary = []
    for job in JOBS:
        did = job["id"]
        print(f"\n=== {did.upper()} ===")
        shutil.copy2(job["g1"], os.path.join(G1_OUT, f"{did}.csv"))
        print(f"  G1 CSV copied -> {did}.csv")

        print(f"  Fitting PREDICTED ({job['pred']['gender']})...")
        vp, fps_p = run_smpl(job["bvh"], job["pred"]["height"], job["pred"]["weight"], job["pred"]["gender"])
        save_verts(vp, fps_p, os.path.join(SMPL_OUT, f"{did}_predicted.bin"))

        print(f"  Fitting GT ({job['gt']['gender']})...")
        vg, fps_g = run_smpl(job["bvh"], job["gt"]["height"], job["gt"]["weight"], job["gt"]["gender"])
        save_verts(vg, fps_g, os.path.join(SMPL_OUT, f"{did}_gt.bin"))

        summary.append((did, vp.shape[0], fps_p))

    print("\n=== Config-paste summary (numFrames, fps) ===")
    for did, nf, fps in summary:
        print(f"  {did}: numFrames={nf}, fps={fps}")


if __name__ == "__main__":
    main()
