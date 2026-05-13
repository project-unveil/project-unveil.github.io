"""Quick verifier: confirm exercising_*.bin contains a male SMPL body shape
by computing shoulder-vs-hip width ratio on frame 0. Male SMPL templates have
a higher shoulder/hip width ratio than female (broader shoulders).
"""
import os, struct
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def load_first_frame(path):
    with open(path, "rb") as f:
        nf = struct.unpack("<I", f.read(4))[0]
        nv = struct.unpack("<I", f.read(4))[0]
        fps = struct.unpack("<f", f.read(4))[0]
        raw = f.read(nv * 3 * 4)
    v = np.frombuffer(raw, dtype=np.float32).reshape(nv, 3)
    return v, nf, fps


def width_at_height(verts, y_frac, band=0.02):
    """Width (X-range) of vertices in a Y-band centered at y_frac of total height."""
    y_min, y_max = verts[:, 1].min(), verts[:, 1].max()
    h = y_max - y_min
    y_target = y_min + y_frac * h
    mask = np.abs(verts[:, 1] - y_target) < band * h
    if mask.sum() < 5:
        return 0.0
    return verts[mask, 0].max() - verts[mask, 0].min()


def main():
    refs = [
        ("exercising_predicted.bin", "should be MALE (h=163,w=57)"),
        ("exercising_gt.bin",        "should be MALE (h=167,w=52)"),
        ("gesture_predicted.bin",    "known MALE (h=176,w=62)"),
        ("gesture_gt.bin",           "known MALE (h=179,w=67)"),
        ("walking_predicted.bin",    "known FEMALE (h=175,w=57)"),
        ("walking_gt.bin",           "known FEMALE (h=171,w=62)"),
        ("sitting_predicted.bin",    "known FEMALE (h=174,w=56)"),
        ("kneeling_predicted.bin",   "known MALE (h=173,w=83)"),
    ]
    for name, note in refs:
        path = os.path.join(HERE, "smpl", name)
        v, nf, fps = load_first_frame(path)
        w_shoulder = width_at_height(v, 0.80)
        w_hip      = width_at_height(v, 0.50)
        ratio = w_shoulder / max(w_hip, 1e-6)
        print(f"{name:36s} sh={w_shoulder:.3f}m hip={w_hip:.3f}m  "
              f"ratio={ratio:.3f}   [{note}]")
    print()
    print("Interpretation: male SMPL templates typically have shoulder/hip > 1.0")
    print("                female SMPL templates typically have shoulder/hip < 1.0")


if __name__ == "__main__":
    main()
