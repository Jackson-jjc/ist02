# Reproducibility guide

## Scope

This repository releases the code and aggregate reference outputs for the published SC-TAS experiments. It does not redistribute the TUD datasets or the manuscript files.

The implementation uses fixed SC-TAS parameters throughout the reported experiments:

- `alpha = 1.0`
- `beta = 0.3` for the no-reference (NR) variant
- `beta = 0.5` for the full-reference (FR) variant
- `tau = 0.83`
- geometric shrinkage factor `eta = 0.9`
- JPEG block size `8 x 8`

## Evaluation protocol

- R2 contains 40 source contents and four JPEG-compressed stimuli per content, for 160 stimuli.
- Learned R2 baselines use leave-one-content-out evaluation, so stimuli derived from the held-out source content do not occur in the training fold.
- R1 contains 29 pristine images and is used for the stability experiment.
- INT contains 54 stimuli: six contents, three distortion types, and three levels.
- INT evaluation is zero-shot. SC-TAS coefficients are fixed from R2, and learned baselines are trained on all R2 data without INT re-tuning.
- The default random seed is 42 where random sampling or optimisation is used.

The primary metrics are Pearson correlation coefficient (CC) and Jensen--Shannon divergence (JSD). The supplementary scripts also compute SIM, KL divergence, AUC-Top20, entropy, centroid shift, and background attention mass.

## Recommended execution order

From `TAS_experiments/`:

```bash
python validate_setup.py --datasets all --include-unet
python smoke_test.py
python run_revised_experiment.py
python run_crossdataset_baselines.py
python run_unet_lite_baseline.py
python run_ablation_sensitivity_experiments.py
python run_supplementary_experiments.py
python run_centerbias_experiment.py
python run_w4_mechanism.py
```

The U-Net-lite experiment is the most hardware-dependent stage. Its architecture has 118,129 trainable parameters, uses 128 x 128 inputs, Adam with learning rate `1e-3`, and early stopping with patience 15. The archived run used an NVIDIA A100 GPU. The code fixes the NumPy and PyTorch seeds, but small differences can still occur across PyTorch, CUDA, cuDNN, CPU/GPU, and operating-system versions.

Python 3.12 is recommended. The original compute logs recorded Python 3.12 and the GPU model, but did not capture a complete package lock file. Consequently, exact bit-for-bit equality is claimed only for the deterministic SC-TAS pipeline, not for the fitted Ridge, MLP, or U-Net-lite baselines. Future runs should retain the output of `python validate_setup.py` together with their result tables because the validator prints the installed package versions.

## Expected outputs

Each experiment writes CSV and/or JSON outputs to a named subdirectory below the configured results root:

| Script | Output directory |
|---|---|
| `run_revised_experiment.py` | `revised_real/` |
| `run_crossdataset_baselines.py` | `crossdataset_baselines/` |
| `run_unet_lite_baseline.py` | `unet_lite_baseline/` |
| `run_ablation_sensitivity_experiments.py` | `ablation_sensitivity/` |
| `run_supplementary_experiments.py` | `supplementary/` |
| `run_centerbias_experiment.py` | `centerbias_sensitivity/` |
| `run_w4_mechanism.py` | `w4_mechanism/` |

Corresponding archived tables are stored under `reference_results/`. During the release audit, a complete R2 run of the deterministic SC-TAS pipeline reproduced the archived aggregate table within `7.75e-7` and the per-stimulus table within `3.14e-5`; R1 and INT SC-TAS results also matched the archived values. For Ridge, MLP, and U-Net-lite, use the archived tables as the record of the published run and treat a new run as a software- and hardware-dependent replication. Do not interpret numerical changes in those fitted baselines as changes to the fixed SC-TAS method.

Run the included consistency check from the repository root:

```bash
python verify_reference_results.py
```

## Important interpretation notes

- SC-TAS NR does not improve R2 CC over the free-viewing prior. Its reported advantage on R2 is distributional: lower JSD and KL and higher SIM.
- On INT, SC-TAS NR does not outperform the prior on CC. The result supports limited degradation and distributional stability rather than universal out-of-domain correction.
- The stability constraint is inactive at the default `beta = 0.3` setting and becomes useful in the deliberately aggressive artifact-weight stress test.
- The component-ablation script evaluates resized component maps and should be compared with the component-ablation reference table, not substituted for the full-resolution main table.

## Troubleshooting

- If validation reports a missing dataset, verify the environment-variable path and the directory names, including `Saliency Maps` in INT.
- If R2 saliency files are missing, confirm that each stimulus has a matching `_COMBINED.jpg` file in both saliency directories.
- If PyTorch installation requires a CUDA-specific wheel, follow the official PyTorch installation instructions for the local CUDA version, then install `requirements-core.txt`.
- Never place dataset files, model checkpoints, or generated results under version control; these paths are excluded by `.gitignore`.
