# UNVEIL Project Page — CLAUDE.md

This directory hosts the **project webpage** for the UNVEIL paper ("Inverting Retargeting: Humanoid Datasets Remember Their Operators", anonymous NeurIPS 2026 submission). The page is a static site deployed via GitHub Pages — no build system, just open `index.html` or run `python -m http.server 8000`.

The user (sihata@uci.edu, UCI) is the paper author and treats this directory as the deployment artifact. The companion repo with experiments and the dataset lives at `C:/Users/sihat/Downloads/bones-seed/` (see "Sibling repo" below).

## What the paper says (one-paragraph version)

Human-to-humanoid motion retargeting solves frame-by-frame inverse kinematics: it matches landmark positions on a shared robot skeleton (Unitree G1) and *intentionally discards body shape*. The paper's surprising finding is that this transform places no objective over how joints move *across time*, so **operator-specific movement dynamics — joint velocity profiles, ranges of motion, coordination rhythms shaped by physiology — survive retargeting and can be inverted back into the operator's biometric attributes**. On BONES-SEED (522 operators, 142K G1-retargeted sequences), UNVEIL gets gender 96.0% / Re-ID 97.2% Top-1 on seen operators, and gender 83.4% / age ±4.2 yr / height ±5.7 cm / weight ±9.1 kg on operators never seen during training. The paper also proposes an operator-aware anonymizer that drops Re-ID 97.2 → 16.8% with only 9 pp action-recognition utility loss. Detailed paper notes: see `memory/unveil_paper.md`.

## Site structure

```
invert/
├── index.html              # Single-page Bootstrap 5 site (~450 lines)
├── assets/
│   ├── css/style.css       # Custom styles
│   ├── js/main.js          # Navbar, fade-ins, demo selector, master sync controller, PDF.js renderer
│   ├── img/                # PDF figures (teaser, framework, comparison) + favicon
│   ├── video/              # MP4 placeholders (g1_robot, predicted, groundtruth)
│   ├── file/Submission.zip # Code release for the submission
│   └── demos/
│       ├── demos_config.json     # Per-activity attributes + file paths (15 activities)
│       ├── g1_csv/<id>.csv       # G1 trajectories for the activity selector
│       ├── smpl/<id>_gt.bin      # SMPL vertex sequences (binary)
│       ├── smpl/<id>_predicted.bin
│       ├── smpl/faces.bin        # Shared SMPL triangle indices
│       └── generate_all_demos.py # Regenerates demos from bones-seed source files
├── g1_engine/              # Embedded G1 robot viewer (iframe in demo section)
├── smpl_engine/            # Embedded SMPL human-body viewer (two iframes: predicted + GT)
├── README.md               # User-facing readme (deploy instructions)
└── watch.ps1               # File watcher: auto-commits + pushes to origin/main on save
```

The site has six sections (in order): hero → demo blocks (the synced viewers) → abstract → teaser figure → method → results table → BibTeX → footer. The demo section now contains **three independent blocks** — each is a self-contained `[Activity dropdown] + [3-panel grid: G1 | predicted | GT] + [per-block sync bar]`. Default activities are walking / dancing / sitting (locomotion / dance / idle) so the leakage finding is visible across motion types without any interaction. Each block has its own master clock, its own predicted-vs-GT attribute chips (color-coded by error magnitude — green vivid → muted sage as |pred−gt|/MAE goes 0 → 2), and its own dropdown for switching that row's activity.

Iframes are lazy-loaded: each iframe carries `data-src` instead of `src`, and an `IntersectionObserver` (rootMargin 300px) hydrates the URL only when the block scrolls within range. Block 0 loads on page open; blocks 1–2 wait until the user scrolls. Each iframe's URL carries a `?demo=<id>` parameter so the engine loads the right activity from the start (no "default → swap" flash).

## How the viewers work

Both viewers are vanilla Three.js (r128, CDN-loaded), each with its own `viewer.html` + `config.json`. They run in iframes inside `index.html` and are slaved to a master sync controller in `assets/js/main.js`. The parent posts `SYNC` (time, playing, speed), `LOAD_DEMO` (switch activity), `PRELOAD_DEMO` (warm cache), and `CAMERA` (cross-viewer orbit sync) messages; the children honor them and `body.embedded { #controls: none }` hides the local play bars. The G1 viewer also broadcasts `READY` once loaded so the parent knows to start playing.

### G1 viewer (`g1_engine/viewer.html`)

**One-time setup (offline)**: `generate_model.py` parses `model/g1_29dof.xml` → `model/g1_model.json` — a flat list of 30 bodies, each with `{name, parent, pos, quat, joint:{name,type,axis}, meshes:[{name,rgba,pos,quat}]}`. There are 60 STL meshes total under `meshes/` (head, pelvis, torso, limbs, fingers, hands).

**Camera & orientation config** (matches SMPL viewer's schema):
- `camera.position` / `camera.target` — absolute camera setup, mirrors `smpl_engine/config.json`. Falls back to legacy `cameraAzimuth` / `cameraElevation` / `cameraDistance` if absent.
- `worldYawDeg` — Y-axis rotation applied to a parent group wrapping `robotWorld`, lets you spin the whole robot to align its facing direction with the SMPL human (which uses BVH conventions). For the default `dancing` demo (macarena) the correct value is **`0`** — robot's frame-0 forward already lands on +Z. Other demos may need a different yaw; iterate by pausing at frame 0 and adjusting in increments of 15° / 45°.

**Boot sequence**:
1. Fetch `config.json` (camera, background, `enhancedMaterials` flag toggling PBR vs Phong).
2. Fetch `model/g1_model.json`.
3. Parse the G1 trajectory CSV via PapaParse — header: `Frame, root_translateX/Y/Z, root_rotateX/Y/Z, <29 joint DOFs>` (columns named `*_dof`, e.g. `left_hip_pitch_joint_dof`). CSV values are **cm + degrees** as written by retargeting. The viewer:
   - converts root translation cm → m (×0.01),
   - converts root rotation deg → rad and constructs a **ZYX-Euler** quaternion stored as `[w,x,y,z]`,
   - converts each joint angle deg → rad,
   - downsamples to `cfg.maxFrames` (default 600) by uniform stride.
4. Build a `THREE.Group` per body. Two-level grouping per body:
   - **outer group** = pos + rest quaternion from the XML (parent-relative offset),
   - **inner group** = joint rotation (animated each frame).
   STLs are loaded via `STLLoader`, attached to the inner group with their per-mesh local pos/quat.
5. The `robotWorld` group rotates `-π/2` around X to convert MuJoCo Z-up → Three.js Y-up.

**Per-frame update**: set the root group's pos+quat from `motionData`, and for every body whose XML `<joint type="hinge">` has a name matching the CSV: `quaternion = setFromAxisAngle(joint.axis, jointAngleRad)` on the inner group. Materials are cached; in `enhancedMaterials` mode the head and dark/light parts get distinct `MeshStandardMaterial` PBR settings (metalness 0.45/0.65/0.15, roughness 0.30/0.35/0.45), plus a cool blue rim light from the upper-back-left.

### SMPL viewer (`smpl_engine/viewer.html`)

**One-time setup (offline)**: `generate_smpl.py` (or `assets/demos/generate_all_demos.py` for batch) reads a SOMA-Uniform BVH file, plus per-actor (height, weight, age, gender), then calls `BVHMotionZYX` and `fit_smpl` from an external `BVH2SMPL/src` library to produce SMPL vertex sequences. Output is a custom packed-binary format:

```
verts.bin  layout (little-endian):
  bytes  0-3 : uint32   num_frames
  bytes  4-7 : uint32   num_verts    (always 6890 for SMPL)
  bytes  8-11: float32  effective_fps
  bytes 12+  : float32[num_frames * 6890 * 3]  XYZ per vertex per frame

faces.bin  layout:
  bytes  0-3 : uint32   num_faces    (13776 for SMPL)
  bytes  4+  : uint32[num_faces * 3] triangle indices (shared across all SMPL bodies)
```

The URL param `?seq=predicted` vs `?seq=groundtruth` selects which `vertsFile` from `config.json` to load. `?embed=1` hides local controls.

**Boot sequence**:
1. Fetch `config.json` — has separate `predicted` and `groundTruth` blocks each carrying `{height, weight, age, gender, vertsFile, bgColor}`. Edit these and re-run `generate_smpl.py` to refresh.
2. Fetch the verts.bin (sequence-specific) and faces.bin (shared) in parallel.
3. Build a single `THREE.BufferGeometry` with a 6890×3 position attribute and 13776×3 indices. Material is `MeshPhongMaterial` (skin color `[0.94, 0.76, 0.58]`, doubleSide).
4. **Floor alignment heuristic** (important): for each frame, find min-Y across all 6890 verts; sort the per-frame minima; take the 10th percentile and use it as the mesh's Y-offset. The comment in the source explains why: frame-0-only underfits (toe tip), global min overfits (a hand vertex passing below the floor); the 10th percentile gives "standing-frames level — feet planted, not floating".

**Per-frame update**: copy the `numVerts*3` slice for frame `fi` into the position attribute, set `needsUpdate`, recompute vertex normals. There's no skinning at runtime — the verts are pre-baked per frame.

**Demo switching**: `LOAD_DEMO` triggers `loadVertsBin` for the activity-specific file, caches by `<id>_<gt|pred>` key, recomputes the floor offset, and reattaches the index buffer. `PRELOAD_DEMO` is a best-effort warm-cache hint dispatched in the background a few seconds after page load for the top demos.

### Per-block sync (in `assets/js/main.js`)

Each `.demo-block` has its own controller. On init, `init()` walks every block, populates its dropdown with all 15 activities (selecting the one named in `data-default-demo`), seeds `block._seqDuration` from that demo's `numFrames / fps`, applies initial chip color coding, wires the dropdown's `change` event to `sendDemoToBlock(block, demo)`, and calls `attachSync(block)`.

`attachSync(block)` installs an independent rAF loop driving that block's `masterTime`, broadcasting `{type:'SYNC', time, playing, speed}` to its 3 iframes via `block.querySelectorAll('iframe').contentWindow.postMessage`. Each block has its own `playing` flag, scrub position, and speed select — they don't talk to each other. Auto-play kicks in per block when one of its iframes posts a `READY` message.

Duration comes from the active demo's `numFrames / fps` — the FPS is **per-activity** (walking 17.4 fps, jogging 25.5 fps, dancing 10.9 fps, sitting 29 fps). When the dropdown changes, `block._seqDuration` is updated and the next tick picks it up.

## Sibling repo: `C:/Users/sihat/Downloads/bones-seed/`

The training code, dataset, and paper PDF live there, not here. Important paths:

- `unveil-neurips.pdf` — the submitted paper (text extraction at `unveil-neurips.txt`).
- `Submission/unveil.py` — supplementary code, three backbone variants (`stream-attn`, `dyn-graph`, `proto-mem`).
- `g1/csv/{date}/<motion>.csv` — full G1-retargeted dataset.
- `soma_uniform/bvh/{date}/<motion>.bvh` — SOMA Uniform skeleton motions (input to `generate_smpl.py`).
- `soma_proportional/bvh/{date}/<motion>.bvh` — per-actor proportional skeleton.
- `soma_shapes/` — shape parameter `.npz` files (uniform shared, proportional per-actor).
- `metadata/seed_metadata_v003.parquet` — 51 cols × 142,220 rows (motion identity + 4 NL descriptions + actor biometrics).
- `metadata/seed_metadata_v002_temporal_labels.jsonl` — NVIDIA Kimodo phase segmentation.

For deeper detail on the dataset layout and the paper's architecture/results, see `memory/bones_seed_dataset.md` and `memory/unveil_paper.md`.

## Conventions and gotchas

- **G1 CSV units are cm + degrees** (not m + rad). Translation gets ×0.01; rotations get ×π/180.
- **Coordinate spaces**: G1/MuJoCo is Z-up; Three.js is Y-up. The G1 viewer applies a single `-π/2` X-rotation on `robotWorld` to convert.
- **Quaternion convention**: model JSON stores `[w,x,y,z]`; Three.js wants `[x,y,z,w]`. The viewer reorders explicitly at every load site.
- **Root rotation Euler order is ZYX** (matches the BVH source).
- **The SMPL faces file is shared across all activities and across predicted/GT** — generate it once.
- **Demo FPS varies per activity**, embedded in each verts.bin header. Don't assume 30 or 120.
- **`watch.ps1` auto-commits and pushes** any file change in this directory after a 2-second debounce. If you don't want a change pushed, stop the watcher first.
- **The site uses `<meta name="robots" content="noindex, nofollow">`** while the submission is anonymous — don't remove that until the paper is de-anonymized.
- **The Submission code does not expand UNVEIL as a backronym anymore** — the paper introduces it as a name only. The earlier "Universal Non-intrusive Evaluation via Invariant Latent representations" line was removed from `bones-seed/Submission/README.md`.

## Memory

Persistent context for future sessions lives in `C:/Users/sihat/.claude/projects/C--Users-sihat-Downloads-invert/memory/`:

- `MEMORY.md` — index.
- `bones_seed_dataset.md` — dataset structure (G1 CSV / SOMA BVH / shapes / metadata).
- `unveil_paper.md` — paper architecture, results, ablations, partial correlations, anonymization.
