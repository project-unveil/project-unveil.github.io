"""One-off: regenerate SMPL binaries for demos whose height/weight/gender
changed in demos_config.json after the user's manual edits.

Run with:
    C:/Users/sihat/miniconda3/envs/animation/python.exe _regen_updated.py
"""
import os, sys, struct
import numpy as np

HERE         = os.path.dirname(os.path.abspath(__file__))
BVH2SMPL_SRC = r"C:\Users\sihat\Downloads\BVH2SMPL\src"
SMPL_DIR     = os.path.join(BVH2SMPL_SRC, "rendering_utils", "smpl")
SMPL_MODELS  = {
    "male":   os.path.join(SMPL_DIR, "basicmodel_m_lbs_10_207_0_v1.0.0.pkl"),
    "female": os.path.join(SMPL_DIR, "basicModel_f_lbs_10_207_0_v1.0.0.pkl"),
}
SMPL_OUT     = os.path.join(HERE, "smpl")
MAX_FRAMES   = 150

# Each entry: (bvh_path, output_bin_name, height_cm, weight_kg, gender)
JOBS = [
    # gesture
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\240529\neutral_alone_R_001__A542.bvh",
     "gesture_predicted.bin", 176, 62, "male"),
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\240529\neutral_alone_R_001__A542.bvh",
     "gesture_gt.bin",        179, 67, "male"),
    # jumping
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\240527\neutral_dancecard_jump_002__A534.bvh",
     "jumping_predicted.bin", 183, 57, "male"),
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\240527\neutral_dancecard_jump_002__A534.bvh",
     "jumping_gt.bin",        179, 51, "male"),
    # sitting
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\240918\sit_on_heels_loop_009__A548.bvh",
     "sitting_predicted.bin", 174, 56, "female"),
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\240918\sit_on_heels_loop_009__A548.bvh",
     "sitting_gt.bin",        171, 60, "female"),
    # climbing_box
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\240529\neutral_come_down_50cm_box_R_001__A542.bvh",
     "climbing_box_predicted.bin", 175, 74, "male"),
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\240529\neutral_come_down_50cm_box_R_001__A542.bvh",
     "climbing_box_gt.bin",        179, 70, "male"),
    # standing_idle
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\230713\pull_shoudler_180_standing_R_001__A428.bvh",
     "standing_idle_predicted.bin", 187, 56, "male"),
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\230713\pull_shoudler_180_standing_R_001__A428.bvh",
     "standing_idle_gt.bin",        183, 52, "male"),
    # crawling (predicted only — gt weight unchanged)
    (r"C:\Users\sihat\Downloads\bones-seed\soma_uniform\bvh\230509\spider_crawl_R_001__A360.bvh",
     "crawling_predicted.bin", 177, 75, "male"),
]


def save_verts(verts, fps, path):
    nf, nv, _ = verts.shape
    with open(path, "wb") as f:
        f.write(struct.pack("<II", nf, nv))
        f.write(struct.pack("<f", float(fps)))
        f.write(verts.astype(np.float32).ravel().tobytes())
    print(f"    -> {os.path.basename(path)}  ({nf}fr, {os.path.getsize(path)/1e6:.1f}MB)")


def run_smpl(bvh_path, height, weight, gender):
    sys.path.insert(0, BVH2SMPL_SRC)
    os.chdir(BVH2SMPL_SRC)
    from soma_viewer import BVHMotionZYX, fit_smpl
    bvh = BVHMotionZYX(os.path.abspath(bvh_path))
    nf  = bvh.motion_length
    verts, _faces = fit_smpl(
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
    for i, (bvh, name, h, w, g) in enumerate(JOBS, 1):
        print(f"\n[{i}/{len(JOBS)}] {name}  (h={h}cm w={w}kg gender={g})")
        verts, fps = run_smpl(bvh, h, w, g)
        save_verts(verts, fps, os.path.join(SMPL_OUT, name))
    print("\nAll done.")


if __name__ == "__main__":
    main()
