# IST02: Task-Adaptive Saliency Analysis

A comprehensive study on image quality assessment using task-adaptive saliency metrics based on eye-tracking data from the TUD datasets.

## Project Overview

This project investigates how visual attention patterns (saliency) vary across different tasks and image compression levels, providing insights into task-dependent image quality metrics.

## Directory Structure

```
IST02/
├── TAS_experiments/          # Task-Adaptive Saliency experiments
│   ├── src/                  # Python source code
│   ├── requirements.txt       # Python dependencies
│   ├── run_*.py              # Experiment scripts
│   ├── submit_*.slurm        # SLURM batch submission scripts
│   └── README.md             # Detailed experiment documentation
│
├── paper/                    # Paper and LaTeX documents
│   └── TUD_final/           # Final paper materials
│
└── README.md                 # This file
```

## Datasets

This study uses the **TUD eye-tracking image quality datasets**, which are publicly available at:

- **Eye-Tracking Release 1**: https://ii.tudelft.nl/iqlab/eye_tracking_1.html
- **Eye-Tracking Release 2**: https://ii.tudelft.nl/iqlab/eye_tracking_2.html
- **Interactions Dataset**: https://ii.tudelft.nl/iqlab/interactions.html

### Dataset Structure:

To run the experiments, download the datasets from the links above and organize them in the project directory:

```
SC-TAS/
├── TUD_Task_EyeTracking/        # Eye-Tracking Release 2
│   ├── OriginalContent/         # Reference images
│   ├── TestImages/              # JPEG compressed images
│   ├── SaliencyFreeLook/         # Free-viewing saliency maps
│   └── SaliencyScoring/          # Task-based saliency maps
│
├── TUD_LIVE_EyeTracking/         # LIVE dataset
│   ├── TUD_LIVE_EyeTracking/
│   │   ├── SaliencyMaps/
│   │   └── TestImages/
│
└── TUD_Interactions/             # Interactions dataset
    ├── images/
    └── Saliency Maps/
```

Please refer to the TUD Image Quality Lab for dataset licensing and access conditions.

## Quick Start

### 1. Install Dependencies

```bash
cd TAS_experiments
pip install -r requirements.txt
```

### 2. Setup Datasets

Download the datasets from the links above and organize them as shown in the structure above.

### 3. Run Experiments

```bash
# Option 1: Run all experiments locally (requires 4-8 hours)
python run_all_experiments.py

# Option 2: Submit to SLURM cluster
sbatch submit_experiments.slurm
```

## Experiment Details

The project includes three main research questions:

### RQ1: Task Shift Analysis
How do visual attention patterns change across different tasks when images are compressed?

### RQ2: Saliency Prediction
Can task-based saliency be predicted from free-viewing attention and compression artifacts?

### RQ3: Practical Application
What is the practical value of task-adaptive metrics for image quality assessment?

## Project Structure

### Core Modules (`TAS_experiments/src/`)

- `config.py` - Configuration management
- `data_loader.py` - Data loading and preprocessing
- `tas_model.py` - Task-Adaptive Saliency model
- `artifact_maps.py` - Compression artifact detection
- `metrics.py` - Saliency evaluation metrics
- `visualizer.py` - Visualization utilities

### Experiment Scripts

- `run_comprehensive_experiment.py` - Full experimental pipeline
- `run_revised_experiment.py` - Revised analysis
- `generate_paper_figures.py` - Publication-quality visualizations

## Requirements

- Python 3.7+
- NumPy, SciPy, Pandas
- OpenCV, Pillow
- Matplotlib, scikit-image
- See `TAS_experiments/requirements.txt` for complete list

## Paper

The paper and LaTeX materials are located in `paper/TUD_final/`.

## Citation

If you use this code or datasets, please cite:

```
@dataset{tudelft_eye_tracking,
  title={TUD Eye-tracking Image Quality Datasets},
  author={TU Delft Image Quality Lab},
  url={https://ii.tudelft.nl/iqlab/},
  year={2023}
}
```

## License

Please refer to the TUD Image Quality Lab for dataset licensing conditions.

## Support

For detailed documentation on running experiments, see [TAS_experiments/README.md](TAS_experiments/README.md).
