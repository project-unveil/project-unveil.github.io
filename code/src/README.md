# UNVEIL — BONES-SEED Supplementary Code

**UNVEIL**  is the
training and evaluation framework used in the paper. 

---

## Variants

| Flag | Description |
|---|---|
| `stream-attn` | Streamed-input attention-pooled graph encoder; per-stream embeddings (position / velocity / acceleration) fused via a learned joint adjacency and attention pooling over temporal segments |
| `dyn-graph` | Dynamic-adjacency multi-stage spatiotemporal network with multi-scale dilated temporal convolutions and global average pooling |
| `proto-mem` | Memory-augmented spatiotemporal network with a learned latent prototype module and class-conditional contrastive regularization |
| `unveil-vanilla` | Hierarchical spatiotemporal GCN baseline with a two-level joint hierarchy (intra-limb + limb-torso) and a learned kinematic encoder over raw position-only input |


## Dependencies

```
torch >= 2.0
numpy
pandas
scikit-learn
mmcv          # required for proto-mem only
triton        # required for torch.compile (optional; use --no-compile if not available)
```

---

## Quick start

```bash
# Re-ID with stream-attn on G1 data (default variant)
python Submission/unveil.py --variant stream-attn --format g1 --task reid

# Gender classification with dyn-graph on uniform BVH
python Submission/unveil.py --variant dyn-graph --format uniform --task gender

# Age regression with proto-mem on proportional BVH
python Submission/unveil.py --variant proto-mem --format proportional --task age

# Re-ID with the vanilla hierarchical GCN baseline (G1)
python Submission/unveil.py --variant unveil-vanilla --format g1 --task reid

# Gender with the vanilla baseline on BVH
python Submission/unveil.py --variant unveil-vanilla --format uniform --task gender

# Run all privacy tasks with stream-attn
python Submission/unveil.py --variant stream-attn --format g1 --task all

# Quick dry-run (limited data, 1 epoch)
python Submission/unveil.py --variant unveil-vanilla --task reid --max-train 200 --max-test 100 --epochs 1
```

---

## The `unveil-vanilla` variant

A clean hierarchical spatiotemporal GCN baseline. Unlike `stream-attn` (which feeds position
+ velocity + acceleration as three explicit input streams), `unveil-vanilla` consumes only
the raw **position** trajectory and learns the temporal dynamics inside a kinematic encoder.

### Pipeline

1. **Joint reshape** (no padding for BVH; small zero-padding for G1):
   - **G1** : `(B, 35, T)` raw DoFs → `(B, 15, 3, T)` — 35 G1 DoFs grouped into 15 semantic joints, ≤ 3 DoFs per joint, zero-padded to a uniform 3-channel feature.
   - **BVH** : `(B, 72, T)` rotation channels → `(B, 24, 3, T)` — direct reshape (24 joints × 3 rotation channels).

2. **Kinematic encoder** — a `Conv1d(C_in=3 → 64, kernel=9, padding=4)` applied independently
   to each joint, followed by BN + ReLU. This replaces the explicit velocity/acceleration
   computation in `stream-attn`: the network learns motion dynamics directly from position.

3. **Hierarchical spatial GCN** — 9 weight matrices per spatial layer:
   - **Hierarchy 1 (intra-limb, 5 subgraphs)**: left-arm, right-arm, left-leg, right-leg, torso.
   - **Hierarchy 2 (limb-torso, 4 subgraphs)**: each limb plus its connecting torso joint.
   - Adjacencies are symmetric-normalized D⁻½AD⁻½ with self-loops.

4. **Temporal convolution** — `Conv2d(kernel=(1,9))` shared across all joints, applied after
   each spatial layer.

5. **10 spatiotemporal blocks** with residual connections. Channel / stride schedule:

   | Layers | In → Out | Stride |
   |---|---|---|
   | 1–4 | 64 → 64 | 1 |
   | 5 | 64 → 128 | 2 |
   | 6–7 | 128 → 128 | 1 |
   | 8 | 128 → 256 | 2 |
   | 9–10 | 256 → 256 | 1 |

   After the 10 blocks: `(B, J, 256, T/4)`.

6. **Global average pool** over both joints (J) and time (T) → `(B, 256)`.

7. **Heads** (shared with the other variants):
   - Re-ID: `Linear(256, num_actors)` + CE-with-label-smoothing + SupCon (warmup 20 epochs)
   - Gender: `Linear(256, 2)` + CE-with-label-smoothing
   - Age / Height / Weight: `Linear(256, 1)` + MSE

### G1 joint grouping (15 joints, all 35 DoFs covered)

| Joint | DoF indices | # |
|---|---|---|
| Pelvis | 0–2 | 3 |
| PelvisRot | 3–5 | 3 |
| LeftHip | 6–8 | 3 |
| LeftKnee | 9 | 1 |
| LeftAnkle | 10–11 | 2 |
| RightHip | 12–14 | 3 |
| RightKnee | 15 | 1 |
| RightAnkle | 16–17 | 2 |
| Waist | 18–20 | 3 |
| LeftShoulder | 21–23 | 3 |
| LeftElbow | 24 | 1 |
| LeftWrist | 25–27 | 3 |
| RightShoulder | 28–30 | 3 |
| RightElbow | 31 | 1 |
| RightWrist | 32–34 | 3 |

Joints with fewer than 3 DoFs are zero-padded to a uniform 3-channel feature. Total ~ 4.5M parameters.

### Defaults (per the architecture spec)

| | Value |
|---|---|
| Optimizer | AdamW |
| Learning rate | 1e-3 |
| Weight decay | 1e-4 |
| Batch size | 128 |
| Gradient clip norm | 5.0 |
| Dropout | 0.5 (on the embedding before heads) |
| SupCon warmup | 20 epochs |
| Early-stopping patience | 40 evaluation cycles |
| Max sequence length | 256 frames @ 30 fps (downsampled from 120 fps) |

---

## CLI reference

### Training arguments

| Argument | Default | Description |
|---|---|---|
| `--epochs` | 100 | Number of training epochs |
| `--lr` | variant-specific | Learning rate |
| `--batch-size` | variant-specific | Batch size |
| `--weight-decay` | 1e-4 | AdamW weight decay |
| `--label-smoothing` | 0.05 | Cross-entropy label smoothing |
| `--lambda-supcon` | 0.1 | SupCon loss weight (0 = CE only) |
| `--lambda-proto` | 0.1 | Memory contrastive loss weight (proto-mem only) |
| `--supcon-warmup` | variant-specific | Epoch to start contrastive losses |
| `--supcon-temp` | 0.07 | SupCon temperature |
| `--early-stop` | 40 | Early stopping patience (eval cycles) |
| `--eval-every` | 1 | Evaluate every N epochs |
| `--seed` | 42 | Random seed |

### Architecture arguments

| Argument | Variants | Default | Description |
|---|---|---|---|
| `--emb-dim` | all | 256 | Embedding dimension |
| `--dim1` | stream-attn | 256 | Feature dimension |
| `--seg` | stream-attn | 64 | Temporal segments |
| `--base-channels` | dyn-graph, proto-mem | 64 / 96 | Base channel count |
| `--num-stages` | dyn-graph, proto-mem | 10 | Number of spatiotemporal blocks |
| `--num-prototype` | proto-mem | 100 | Number of latent prototypes |
| `--dropout` | dyn-graph, proto-mem, unveil-vanilla | 0.5 | Dropout rate |
| `--variance-percentile` | all (BVH) | variant-specific | BVH channel variance filtering (0 = keep all) |

### Evaluation arguments

| Argument | Default | Description |
|---|---|---|
| `--reid-eval` | variant-specific | `centroid` (stream-attn default) or `closed-set` (other variants default) |
| `--split-mode` | `user` | `user` = Phase 2 manifests; `user_task` = regenerate from metadata |
| `--deconfound` | `residual` | Embedding deconfounding: `none` or `residual` |
| `--deconfound-key` | `package` | Metadata column for task deconfounding |

### I/O arguments

| Argument | Default | Description |
|---|---|---|
| `--checkpoint-dir` | auto | Checkpoint base directory |
| `--save-every` | 10 | Save periodic checkpoint every N epochs |
| `--max-train` | 0 | Limit training samples (0 = all) |
| `--max-test` | 0 | Limit test samples (0 = all) |
| `--num-workers` | 0 | DataLoader workers |
| `--no-compile` | off | Disable `torch.compile` |

---

## Variant-specific defaults

| Argument | stream-attn | dyn-graph | proto-mem | unveil-vanilla |
|---|---|---|---|---|
| `--lr` | 3e-4 | 1e-3 | 1e-3 | 1e-3 |
| `--batch-size` | 64 | 32 | 32 | 128 |
| `--supcon-warmup` | 20 | 20 | 8 | 20 |
| `--emb-dim` | 256 | 256 | 256 | 256 |
| `--variance-percentile` | 10.0 | 0.0 | 0.0 | 0.0 |
| `--dim1` | 256 | — | — | — |
| `--seg` | 64 | — | — | — |
| `--base-channels` | — | 64 | 96 | — |
| `--num-stages` | — | 10 | 10 | 10 (fixed) |
| `--num-prototype` | — | — | 100 | — |
| `--lambda-proto` | — | — | 0.1 | — |
| `--dropout` | — | 0.5 | 0.5 | 0.5 |
| `--reid-eval` default | centroid | closed-set | closed-set | closed-set |

---

## Checkpoint layout

Each variant × format × task combination writes to its own directory to prevent collisions:

```
artifacts/models/unveil/<variant>/actor_holdout_split_<format>/<task>/
├── best_model.pt
├── checkpoint_epoch010.pt
├── checkpoint_epoch020.pt
├── final_<format>_<task>.pt
└── final_metrics_<format>_<task>.json
```

---

## Train / val / test split

The split is **actor-level**: every actor's motion sequences land entirely in one of `pure_train`, `seen_val`, or `unseen_test`, so reported test metrics are operator-disjoint from training. Split artifacts are written to `artifacts/splits/`.

### Files

| File | Rows (excl. header) | Description |
|---|---|---|
| `train_manifest.csv` | 111,857 | Training rows (originals + mirrors) |
| `val_manifest.csv` | 15,233 | Held-out demos of *seen* actors (validation signal during training) |
| `test_manifest.csv` | 15,002 | All demos of completely *unseen* actors (final reported result) |
| `split_summary.json` | — | Config, integrity checks, and per-actor row counts |
| `top20_action_types_per_category.csv` | 368 | Per-category action whitelist used for category-level analyses |

### Actor partition

492 of the 522 raw actors are eligible (30 are skipped for having fewer than 20 motions). The eligible actors are partitioned as:

| Group | Actors | Description |
|---|---|---|
| `pure_train` | 294 | Appear only in training |
| `seen_val` | 99 | Same actor appears in both train and val; their demos are split row-wise |
| `unseen_test` | 99 | Held out entirely; used only for the final test |

### Split parameters

From `split_summary.json → config`:

| Parameter | Value | Meaning |
|---|---|---|
| `random_state` | 42 | RNG seed (deterministic) |
| `unseen_test_frac` | 0.20 | Fraction of eligible actors held out as unseen test |
| `seen_val_frac` | 0.25 | Fraction of the remaining (training-pool) actors that become seen-val sources |
| `min_motions_per_actor` | 20 | Actors below this threshold are dropped |
| `test_originals_only` | true | Val and test contain originals only — no left/right mirror augmentations |
| `train_val_includes_mirrors` | true | Mirror sequences are allowed in train only |

### Row counts

| Partition | Rows | Originals | Mirrors |
|---|---|---|---|
| Train | 111,857 | 55,945 | 55,912 |
| Val | 15,233 | 15,233 | 0 |
| Test | 15,002 | 15,002 | 0 |
| **Dataset total** | **142,220** | **71,132** | **71,088** |

### Integrity guarantees

Asserted at split-build time (`split_summary.json → integrity`):

- **Zero actor overlap** between train and val (`train_val_actor_overlap = 0`).
- **Zero canonical-motion overlap** between train/test or val/test — a motion and its mirror share a `canonical_motion_key`, so a motion never appears in two partitions even via its mirror.
- **No mirrors in val or test** (`no_mirrors_in_test = true`) — every reported metric is measured on original motions only, so mirror-augmentation leakage cannot inflate scores.

### Manifest schema

Each row in the manifest CSVs has these 18 columns:

```
split, actor_uid, actor_gender, actor_age_yr, actor_height_cm, actor_weight_kg,
move_name, canonical_motion_key, is_mirror, package, category,
content_type_of_movement, content_body_position, content_uniform_style,
move_duration_frames, move_soma_proportional_path, move_soma_uniform_path,
move_g1_mujoco_path
```

`actor_uid` is the operator identifier; the biometric columns (`actor_gender`, `actor_age_yr`, `actor_height_cm`, `actor_weight_kg`) are the regression / classification targets. The three `move_*_path` columns point to the soma_proportional BVH, soma_uniform BVH, and G1 MuJoCo CSV for that sequence.

---

## Evaluation split structure

All variants use a three-way evaluation split:

1. **sa_seen** (seen-actors-seen-demos): 80 % of the `seen_val` actors' demos — used in training; reported for reference
2. **sa_unseen** (seen-actors-unseen-demos): held-out 20 % of `seen_val` actors' demos — used as the primary validation signal during training
3. **unseen** (unseen-actors): the `test_manifest` actors, completely held out — final reported result

The `pure_train` actors from `train_manifest.csv` are combined with the 80 % portion of `seen_val` to form the full training set.

---

## Notes

- **`stream-attn`** processes data as `(B, 3, C, T)` with three-stream (position / velocity / acceleration) input fused internally via learned adjacency. No external model library is required.
- **`dyn-graph`** and **`proto-mem`** reshape input to `(B, 1, T, V, C_in)`: for G1, `V=35, C_in=3`; for BVH, `V=24, C_in=9` (3 rotation channels × 3 streams per joint). These variants require all 72 BVH channels (`--variance-percentile 0.0` is enforced automatically).
- **`unveil-vanilla`** uses **only the position stream** (the velocity / acceleration streams from the dataset are discarded). Input is reshaped to `(B, J, 3, T)` with `J=15` for G1 (semantic joint grouping) and `J=24` for BVH (one joint per body joint). The kinematic encoder learns motion dynamics from position alone. Like `dyn-graph`/`proto-mem`, all 72 BVH channels are required (`--variance-percentile 0.0` is enforced automatically). No external model library is needed.
- The **BONES-SEED skeleton layouts** (`bones_seed_g1`, `bones_seed_bvh`) are already registered in `DS-GCN/pyskl/utils/graph.py`; no patching is required for `dyn-graph`. For `proto-mem`, the graph utility is patched at module load time. `unveil-vanilla` builds its own hierarchical adjacency matrices internally and does not depend on either external library.
- All four variants return `(logits, z, aux)` from `UNVEIL.forward`; `aux` is `None` for `stream-attn`, `dyn-graph`, and `unveil-vanilla`, and contains the reconstructed graph tensor for `proto-mem`.
