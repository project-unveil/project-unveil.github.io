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
    for name in ["exercising_predicted.bin", "exercising_gt.bin"]:
        path = os.path.join(HERE, "smpl", name)
        v, nf, fps = load_first_frame(path)
        # Shoulder band ~ 80% of body height, hip band ~ 50%
        w_shoulder = width_at_height(v, 0.80)
        w_hip      = width_at_height(v, 0.50)
        ratio = w_shoulder / max(w_hip, 1e-6)
        print(f"{name}: frames={nf}, shoulder_w={w_shoulder:.3f}m, "
              f"hip_w={w_hip:.3f}m, shoulder/hip={ratio:.3f}")
    print()
    print("Interpretation: male SMPL templates typically have shoulder/hip > 1.0")
    print("                female SMPL templates typically have shoulder/hip < 1.0")


if __name__ == "__main__":
    main()
