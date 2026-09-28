# SC-TAS: Stability-Constrained Task-Adaptive Saliency

Official implementation and reproducibility material for the CGI 2026 paper:

> **SC-TAS: Stability-Constrained Task-Adaptive Saliency for Artifact-Aware Attention Transfer in JPEG-Compressed Images**
>
> Jiajun Chen, Ya Zhang, and Hongxin Li
>
> *The Visual Computer*, volume 42, article 482, 2026
>
> [Springer article](https://link.springer.com/article/10.1007/s00371-026-04693-7) · [DOI](https://doi.org/10.1007/s00371-026-04693-7)

SC-TAS is a training-free method that adapts a free-viewing saliency prior towards image-quality-scoring attention using JPEG artifact evidence. The stability rule limits excessive drift from the prior when the artifact contribution is deliberately increased.

## What is included

```text
.
├── README.md
├── REPRODUCIBILITY.md
├── CITATION.cff
├── reference_results/               # Tabular outputs used to check reproduction
└── TAS_experiments/
    ├── src/                          # SC-TAS, artifact maps, metrics, data loader
    ├── requirements-core.txt         # Main experiments and learning baselines
    ├── requirements-unet.txt         # PyTorch for U-Net-lite
    ├── requirements.txt              # Complete environment
    ├── validate_setup.py             # Dependency and dataset-layout validator
    ├── smoke_test.py                 # Data-free implementation check
    ├── run_revised_experiment.py     # Main R2 evaluation
    ├── run_crossdataset_baselines.py # R1/INT and Ridge/MLP experiments
    ├── run_unet_lite_baseline.py     # U-Net-lite LOCO and zero-shot evaluation
    ├── run_ablation_sensitivity_experiments.py
    │                                 # Component, sensitivity, stability analyses
    ├── run_supplementary_experiments.py
    ├── run_centerbias_experiment.py  # Prior-quality sensitivity
    └── run_w4_mechanism.py           # Artifact-mechanism analysis
```

The datasets and manuscript source are deliberately not included. Dataset access remains subject to the original providers' conditions.

## Installation

Python 3.12 is recommended and is the version used by the automated checks.

```bash
git clone https://github.com/Jackson-jjc/ist02.git
cd ist02/TAS_experiments
python -m venv .venv
```

Activate the environment:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install all dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For all experiments except U-Net-lite, `requirements-core.txt` is sufficient.

## Datasets

Obtain the research datasets from their original TUD pages. The provider may
require a password or contact request before download:

- [Eye-Tracking Release 1](https://ii.tudelft.nl/iqlab/eye_tracking_1.html)
- [Eye-Tracking Release 2](https://ii.tudelft.nl/iqlab/eye_tracking_2.html)
- [Interactions dataset](https://ii.tudelft.nl/iqlab/interactions.html)

The default layout beside `TAS_experiments/` is:

```text
TUD_Task_EyeTracking/                 # R2
├── OriginalContent/
├── TestImages/
├── SaliencyFreeLook/
└── SaliencyScoring/

TUD_LIVE_EyeTracking/                 # R1 download
└── TUD_LIVE_EyeTracking/
    ├── TestImages/
    └── SaliencyMaps/

TUD_Interactions/
├── images/
│   └── originals/
└── Saliency Maps/
```

If the datasets are elsewhere, set these environment variables:

```bash
SCTAS_R2_ROOT=/path/to/TUD_Task_EyeTracking
SCTAS_R1_ROOT=/path/to/TUD_LIVE_EyeTracking/TUD_LIVE_EyeTracking
SCTAS_INT_ROOT=/path/to/TUD_Interactions
SCTAS_RESULTS_ROOT=/path/to/output              # optional
```

PowerShell example:

```powershell
$env:SCTAS_R2_ROOT = "D:\data\TUD_Task_EyeTracking"
$env:SCTAS_R1_ROOT = "D:\data\TUD_LIVE_EyeTracking\TUD_LIVE_EyeTracking"
$env:SCTAS_INT_ROOT = "D:\data\TUD_Interactions"
```

Validate the installation before running experiments:

```bash
python validate_setup.py --datasets all --include-unet
python smoke_test.py
```

## Reproducing the paper experiments

Run commands from `TAS_experiments/`.

| Paper analysis | Command | Required data |
|---|---|---|
| Main R2 results, RQ1--RQ3, FR/NR SC-TAS | `python run_revised_experiment.py` | R2 |
| R1 stability, INT zero-shot, Ridge and MLP | `python run_crossdataset_baselines.py` | R1, R2, INT |
| U-Net-lite LOCO and INT zero-shot | `python run_unet_lite_baseline.py` | R1, R2, INT |
| Component ablation, full-R2 sensitivity, stability stress test | `python run_ablation_sensitivity_experiments.py` | R2 |
| Extended metrics and ceiling analyses | `python run_supplementary_experiments.py` | R2 |
| Free-viewing-prior sensitivity | `python run_centerbias_experiment.py` | R2 |
| Artifact-map mechanism analysis | `python run_w4_mechanism.py` | R2 |

Outputs are written below `TAS_experiments/results/`, or below `SCTAS_RESULTS_ROOT` when it is set. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the protocol, expected outputs, and interpretation of numerical differences.

## Reference results

The machine-readable tables in [`reference_results/`](reference_results/) are the archived outputs associated with the published analyses. They contain no dataset images or saliency maps. Check their internal consistency with:

```bash
python verify_reference_results.py
```

The primary reported values include:

| Setting | CC | JSD |
|---|---:|---:|
| R2 free-viewing prior | 0.849 | 0.298 |
| R2 SC-TAS NR | 0.827 | 0.281 |
| R2 SC-TAS FR | 0.782 | 0.305 |
| INT SC-TAS NR | 0.670 | 0.324 |
| R1 SC-TAS NR stability vs prior | 0.957 | 0.130 |

These values describe different evaluation targets. In particular, the R1 row measures stability relative to the R1 prior, while R2 and INT rows compare predictions with scoring saliency.

The deterministic SC-TAS implementation was re-run on the complete R2 dataset during the public-release audit. Its aggregate outputs matched the archived tables to within `7.75e-7`, and its per-stimulus outputs to within `3.14e-5`. The trained Ridge, MLP, and U-Net-lite baselines can vary with numerical-library, scikit-learn, PyTorch, CUDA, and hardware versions; the archived tables record the values used in the paper. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the precise comparison policy.

## Citation

```bibtex
@article{Chen2026SCTAS,
  author  = {Chen, Jiajun and Zhang, Ya and Li, Hongxin},
  title   = {{SC-TAS}: Stability-Constrained Task-Adaptive Saliency for Artifact-Aware Attention Transfer in {JPEG}-Compressed Images},
  journal = {The Visual Computer},
  year    = {2026},
  volume  = {42},
  doi     = {10.1007/s00371-026-04693-7},
  url     = {https://doi.org/10.1007/s00371-026-04693-7}
}
```

## Licence and data terms

The TUD datasets are governed by the original providers' access and usage conditions. No dataset files are redistributed here. A separate software licence has not yet been specified for this repository; contact the authors before redistribution or incorporation into another project.
