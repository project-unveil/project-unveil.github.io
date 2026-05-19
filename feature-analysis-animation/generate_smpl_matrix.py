"""
generate_smpl_matrix.py
-----------------------
Fits SMPL meshes for every clip listed in `data/matrix_config.json`. For each
(attribute, clip) the script produces TWO outputs — one per side ("high" /
"low") using the body shape declared in that attribute's `high_shape` /
`low_shape` block. Output binaries land at:

    data/smpl_matrix/<attr>/<clip_id>_high.bin
    data/smpl_matrix/<attr>/<clip_id>_low.bin
    data/smpl_matrix/<attr>/faces.bin            (written once per attr)

The clips are deliberately shorter than the single-pair fits used by
twin_view*.html — matrix panels are tiny, looping continuously, so a 4–6 s
slab fitting through VPoser is plenty visible. Tune `--max-input-frames`
(default 600 = 5 s @ 120 fps) and `--max-frames` (default 100 = 3.3 s @ 30
fps) to trade quality for wall-clock time.

Usage:
  python generate_smpl_matrix.py \
      --bones-seed   C:/Users/sihat/Downloads/bones-seed \
      --bvh2smpl-src C:/Users/sihat/Downloads/BVH2SMPL/src \
      --vposer-dir   C:/Users/sihat/Downloads/BVH2SMPL/vposer_v1_0 \
      --device cuda
      [--attr weight|age|all]
      [--clip-ids dance_hiphop walking ...]   # filter
      [--skip-existing]                        # resume after a crash
"""

import argparse
import json
import os
import struct
import sys
import time
from pathlib import Path

import numpy as np


def save_verts(verts: np.ndarray, fps: float, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    nf, nv, _ = verts.shape
    with open(path, "wb") as f:
        f.write(struct.pack("<II", nf, nv))
        f.write(struct.pack("<f", float(fps)))
        f.write(verts.astype(np.float32).ravel().tobytes())
    print(f"      -> {path.name}  ({nf} frames @ {fps:.1f} fps, {os.path.getsize(path)/1e6:.1f} MB)")


def save_faces(faces: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<I", len(faces)))
        f.write(faces.astype(np.uint32).ravel().tobytes())
    print(f"      -> {path.name}  ({len(faces)} faces)")


GENDER_MODEL = {
    "male":   "basicmodel_m_lbs_10_207_0_v1.0.0.pkl",
    "female": "basicModel_f_lbs_10_207_0_v1.0.0.pkl",
}


def fit_one(label, bvh_abs, smpl_pkl, vposer_dir, shape, bvh2smpl_src, device,
            max_frames, free_arms, z_prior_w, max_input_frames):
    """Fit a single SMPL output. Truncates the BVH to a middle slab so each
    fit completes in tens of minutes rather than hours."""
    from soma_viewer_vposer import fit_smpl_vposer
    from soma_viewer import BVHMotionZYX

    print(f"    [{label}] gender={shape['gender']} {shape['weight_kg']}kg @ {shape['height_cm']}cm")

    # Library expects relative paths from its own working dir.
    os.chdir(str(bvh2smpl_src))
    bvh = BVHMotionZYX(str(bvh_abs))
    nf_src = bvh.motion_length
    if nf_src > max_input_frames:
        start = (nf_src - max_input_frames) // 2
        end = start + max_input_frames
        bvh.joint_position = bvh.joint_position[start:end]
        bvh.joint_rotation = bvh.joint_rotation[start:end]
        # Reset cached FK results so they get recomputed on the slab.
        bvh.joint_translation = None
        bvh.joint_orientation = None
        print(f"      truncate {nf_src} -> {max_input_frames} ({max_input_frames/120.0:.1f}s)")

    t0 = time.time()
    verts, faces = fit_smpl_vposer(
        bvh, scale=100.0,
        smpl_path=str(smpl_pkl),
        vposer_dir=str(vposer_dir),
        device=device,
        height_cm=shape["height_cm"],
        weight_kg=shape["weight_kg"],
        gender=shape["gender"],
        uid=None,
        free_arms=free_arms,
        z_prior_w=z_prior_w,
    )
    verts = np.asarray(verts); faces = np.asarray(faces)
    n = len(verts)
    if n > max_frames:
        idx = np.round(np.linspace(0, n - 1, max_frames)).astype(int)
        verts = verts[idx]
        fps = 120.0 * max_frames / n
    else:
        fps = 120.0
    print(f"      fit done in {time.time()-t0:.1f}s -> {len(verts)} frames @ {fps:.1f} fps")
    return verts, faces, fps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bones-seed",   required=True, type=Path)
    ap.add_argument("--bvh2smpl-src", required=True, type=Path)
    ap.add_argument("--vposer-dir",   required=True, type=Path)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--attr", choices=["weight", "age", "all"], default="all")
    ap.add_argument("--clip-ids", nargs="*", default=None,
                    help="Optional filter — only fit clips with these ids.")
    ap.add_argument("--max-input-frames", type=int, default=600,
                    help="BVH source slab length (frames @ 120 fps). 600 = 5 s.")
    ap.add_argument("--max-frames", type=int, default=100,
                    help="Output frame count after downsampling.")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "data" / "smpl_matrix")
    ap.add_argument("--no-free-arms", dest="free_arms", action="store_false", default=True)
    ap.add_argument("--z-prior-w", type=float, default=0.001)
    ap.add_argument("--skip-existing", action="store_true",
                    help="Skip clips whose output bins already exist (use to resume).")
    args = ap.parse_args()

    bs   = args.bones_seed.resolve()
    src  = args.bvh2smpl_src.resolve()
    vp   = args.vposer_dir.resolve()
    out  = args.out.resolve()
    smpl_dir = src / "rendering_utils" / "smpl"
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(src))

    config_path = Path(__file__).parent / "data" / "matrix_config.json"
    cfg = json.loads(config_path.read_text())

    attrs = ["weight", "age"] if args.attr == "all" else [args.attr]

    total_fits = sum(len(cfg[a].get("clips", []))
                     for a in attrs) * 2
    print(f"Plan: {total_fits} SMPL fits (attrs={attrs}, "
          f"max_input_frames={args.max_input_frames}, max_frames={args.max_frames}, "
          f"device={args.device})")
    print(f"Output: {out}\n")

    done = 0
    for attr_name in attrs:
        attr = cfg[attr_name]
        clips = attr.get("clips", [])
        if not clips:
            print(f"\n=== {attr_name.upper()} === (no clips)")
            continue
        print(f"\n=== {attr_name.upper()} ({len(clips)} clips) ===")
        attr_out = out / attr_name
        faces_path = attr_out / "faces.bin"
        faces_saved = faces_path.exists()

        for clip in clips:
            cid = clip["id"]
            if args.clip_ids and cid not in args.clip_ids:
                continue
            print(f"\n  [{attr_name}/{cid}]  {clip['label']}  ({clip['actor']})")
            bvh_abs = (bs / clip["source_bvh"]).resolve()
            if not bvh_abs.exists():
                print(f"    SKIP — BVH missing: {bvh_abs}")
                continue

            for side in ("high", "low"):
                done += 1
                shape = attr[f"{side}_shape"]
                out_bin = attr_out / f"{cid}_{side}.bin"
                if args.skip_existing and out_bin.exists():
                    print(f"    [{done}/{total_fits}] {side} — skip (exists)")
                    continue
                pkl = smpl_dir / GENDER_MODEL[shape["gender"]]
                if not pkl.exists():
                    print(f"    SKIP — SMPL pkl missing: {pkl}")
                    continue

                label = f"{done}/{total_fits} · {attr_name}/{cid} · {side}"
                verts, faces, fps = fit_one(
                    label=label, bvh_abs=bvh_abs, smpl_pkl=pkl, vposer_dir=vp,
                    shape=shape, bvh2smpl_src=src, device=args.device,
                    max_frames=args.max_frames, free_arms=args.free_arms,
                    z_prior_w=args.z_prior_w,
                    max_input_frames=args.max_input_frames,
                )
                save_verts(verts, fps, out_bin)
                if not faces_saved:
                    save_faces(faces, faces_path)
                    faces_saved = True

    print(f"\nDone — wrote outputs under {out}.")


if __name__ == "__main__":
    main()
