# SC-TAS: Stability-Constrained Task-Adaptive Saliency

Official code repository for the CGI 2026 paper:

> **SC-TAS: Stability-Constrained Task-Adaptive Saliency for Artifact-Aware Attention Transfer in JPEG-Compressed Images**
>
> Jiajun Chen, Ya Zhang, and Hongxin Li
>
> *The Visual Computer*, 42(11), article 482, 2026
>
> [Springer article](https://link.springer.com/article/10.1007/s00371-026-04693-7) · [DOI](https://doi.org/10.1007/s00371-026-04693-7)

## Overview

SC-TAS is a training-free framework that adapts a free-viewing saliency prior towards image-quality-scoring attention using JPEG artifact evidence. The stability constraint keeps the free-viewing prior dominant and acts as a safeguard when artifact injection becomes too strong.

The repository contains the experiment code used for the paper, including:

- the main R2 task-shift and SC-TAS experiments;
- full-reference and no-reference artifact variants;
- cross-dataset evaluation on R1 and the TUD Interactions dataset;
- Ridge, MLP, and U-Net-lite learning baselines;
- component, parameter-sensitivity, stability-stress, and prior-sensitivity analyses; and
- scripts for generating paper figures and supplementary results.

## Repository Structure

```text
.
├── README.md
└── TAS_experiments/
    ├── src/                              # Core implementation
    ├── requirements.txt                  # Python dependencies
    ├── run_revised_experiment.py         # Main R2 experiments
    ├── run_crossdataset_baselines.py     # R1/INT and Ridge/MLP evaluation
    ├── run_unet_lite_baseline.py         # U-Net-lite baseline
    ├── run_revision_response_experiments.py
    │                                     # Ablations, sensitivity, stress test
    ├── run_supplementary_experiments.py  # Supplementary analyses
    ├── run_centerbias_experiment.py      # Prior-quality sensitivity
    └── generate_paper_figures.py         # Figure generation
```

## Datasets

The datasets are not redistributed in this repository. Download them from the TUD Image Quality Lab and follow their licensing and access conditions:

- [Eye-Tracking Release 1](https://ii.tudelft.nl/iqlab/eye_tracking_1.html)
- [Eye-Tracking Release 2](https://ii.tudelft.nl/iqlab/eye_tracking_2.html)
- [Interactions dataset](https://ii.tudelft.nl/iqlab/interactions.html)

For the R2 experiments, arrange the data as follows:

```text
TUD_Task_EyeTracking/
├── OriginalContent/
├── TestImages/
├── SaliencyFreeLook/
└── SaliencyScoring/
```

Release 2 contains 40 source contents and four JPEG-compressed stimuli per source, giving 160 stimuli in total.

## Setup

```bash
git clone https://github.com/Jackson-jjc/ist02.git
cd ist02/TAS_experiments
python -m venv .venv
```

Activate the environment and install the dependencies:

```bash
pip install -r requirements.txt
```

Before running the experiments, set `DATA_ROOT` in [`TAS_experiments/src/config.py`](TAS_experiments/src/config.py) to the local path of the downloaded R2 dataset. The cross-dataset scripts also require the R1 and Interactions datasets to be available locally.

## Running the Experiments

Run the experiment scripts individually from `TAS_experiments/`:

```bash
# Main R2 analysis
python run_revised_experiment.py

# Cross-dataset and lightweight supervised baselines
python run_crossdataset_baselines.py

# U-Net-lite baseline
python run_unet_lite_baseline.py

# Component ablation, full-R2 sensitivity, and stability stress test
python run_revision_response_experiments.py

# Extended metrics and supplementary analyses
python run_supplementary_experiments.py

# Prior-quality / centre-bias sensitivity
python run_centerbias_experiment.py
```

Outputs are written under `TAS_experiments/results/`. Runtime depends on the selected experiment, hardware, and dataset location.

## Main Evaluation Protocol

- **R2 evaluation:** leave-one-content-out (LOCO), preventing the same source content from appearing in both training and test folds for learned baselines.
- **Primary metrics:** Pearson correlation coefficient (CC) and Jensen-Shannon divergence (JSD).
- **Additional metrics:** SIM, KL divergence, AUC-Top20, entropy, centroid shift, and background attention mass.
- **Cross-dataset evaluation:** zero-shot evaluation on pristine R1 images and the multi-distortion Interactions dataset.

## Citation

If you use this repository, please cite the paper.

Springer citation:

> Chen, J., Zhang, Y. & Li, H. SC-TAS: stability-constrained task-adaptive saliency for artifact-aware attention transfer in JPEG-compressed images. *The Visual Computer* **42**, 482 (2026). https://doi.org/10.1007/s00371-026-04693-7

BibTeX:

```bibtex
@article{Chen2026SCTAS,
  author  = {Chen, Jiajun and Zhang, Ya and Li, Hongxin},
  title   = {{SC-TAS}: Stability-Constrained Task-Adaptive Saliency for Artifact-Aware Attention Transfer in {JPEG}-Compressed Images},
  journal = {The Visual Computer},
  year    = {2026},
  volume  = {42},
  number  = {11},
  doi     = {10.1007/s00371-026-04693-7},
  url     = {https://doi.org/10.1007/s00371-026-04693-7}
}
```

## Notes on Reproducibility

- Dataset files are not included and must be obtained from the original providers.
- The current configuration contains a machine-specific default dataset path; update `DATA_ROOT` before execution.
- Some legacy documentation files refer to launcher or validation scripts that are not included in the public repository. Use the existing experiment scripts listed above.

## Licence

Dataset use is governed by the original TUD Image Quality Lab terms. No separate software licence file is currently included in this repository.
