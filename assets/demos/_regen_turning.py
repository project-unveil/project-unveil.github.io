"""One-off: regen pulling_*.bin with updated weights."""
import os, sys, struct
import numpy as np

HERE         = os.path.dirname(os.path.abspath(__file__))
BONES_SEED   = os.environ.get("BONES_SEED_DIR", r"C:\Users\sihat\Downloads\bones-seed")
BVH2SMPL_SRC = os.environ.get("BVH2SMPL_SRC",   r"C:\Users\sihat\Downloads\BVH2SMPL\src")
SMPL_DIR     = os.path.join(BVH2SMPL_SRC, "rendering_utils", "smpl")
SMPL_MODELS  = {
    "male":   os.path.join(SMPL_DIR, "basicmodel_m_lbs_10_207_0_v1.0.0.pkl"),
    "female": os.path.join(SMPL_DIR, "basicModel_f_lbs_10_207_0_v1.0.0.pkl"),
}
SMPL_OUT     = os.path.join(HERE, "smpl")
MAX_FRAMES   = 150
NAME         = "pulling"

BVH  = os.path.join(BONES_SEED, r"soma_uniform\bvh\231019\high_big_crank_ccw_002__A484.bvh")
PRED = dict(height=163, weight=56, gender="female")
GT   = dict(height=167, weight=62, gender="female")


def save_verts(verts, fps, path):
    nf, nv, _ = verts.shape
    with open(path, "wb") as f:
        f.write(struct.pack("<II", nf, nv))
        f.write(struct.pack("<f", float(fps)))
        f.write(verts.astype(np.float32).ravel().tobytes())
    print(f"  -> {os.path.basename(path)}  ({nf}fr, {os.path.getsize(path)/1e6:.1f}MB)")


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
    print("Fitting PREDICTED (male)...")
    vp, fps = run_smpl(BVH, PRED["height"], PRED["weight"], PRED["gender"])
    save_verts(vp, fps, os.path.join(SMPL_OUT, f"{NAME}_predicted.bin"))

    print("Fitting GT (male)...")
    vg, fps2 = run_smpl(BVH, GT["height"], GT["weight"], GT["gender"])
    save_verts(vg, fps2, os.path.join(SMPL_OUT, f"{NAME}_gt.bin"))

    print("Done.")


if __name__ == "__main__":
    main()
