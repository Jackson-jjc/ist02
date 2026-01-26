"""
Configuration for TAS experiments
"""
import os
from pathlib import Path

class Config:
    """Configuration class for TAS experiments"""
    def __init__(self):
        # Base paths
        self.PROJECT_ROOT = Path(__file__).parent.parent
        self.DATA_ROOT = Path('/iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking')
        self.RESULTS_DIR = self.PROJECT_ROOT / 'results'
        self.LOGS_DIR = self.PROJECT_ROOT / 'logs'

        # Data folders
        self.ORIGINAL_CONTENT_DIR = self.DATA_ROOT / 'OriginalContent'
        self.TEST_IMAGES_DIR = self.DATA_ROOT / 'TestImages'
        self.SALIENCY_FREELOOK_DIR = self.DATA_ROOT / 'SaliencyFreeLook'
        self.SALIENCY_SCORING_DIR = self.DATA_ROOT / 'SaliencyScoring'

        # Create output directories
        self.RESULTS_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)

        # Dataset configuration
        self.NUM_CONTENTS = 40  # 40 reference images
        self.NUM_LEVELS = 4     # 4 compression levels per content
        self.NUM_IMAGES = self.NUM_CONTENTS * self.NUM_LEVELS

        # Experiment configuration
        self.COMPRESSION_LEVELS = [10, 11, 20, 64]  # Example levels (will be extracted from filenames)
        self.SEED = 42
        self.VERBOSE = True

        # Preprocessing
        self.EPSILON = 1e-12
        self.SALIENCY_DENOISE_SIGMA = 1.0
        self.IMAGE_RESIZE_METHOD = 'bilinear'

        # Cross-validation
        self.LOCO_FOLD = True  # Leave-One-Content-Out

        # TAS Model parameters (will be optimized during training)
        # Log-linear TAS
        self.ALPHA_DEFAULT = 1.0
        self.BETA_DEFAULT = 1.0
        self.GAMMA_DEFAULT = 0.1

        # Mixture TAS weights
        self.W_FREELOOK_DEFAULT = 0.6
        self.W_ARTIFACT_DEFAULT = 0.3
        self.W_CENTER_DEFAULT = 0.1

        # Metrics
        self.COMPUTE_CC = True
        self.COMPUTE_JSD = True
        self.COMPUTE_ENTROPY = True
        self.COMPUTE_CENTROID_SHIFT = True

        # Outputs
        self.SAVE_FIGURES = True
        self.SAVE_TABLES = True
        self.SAVE_MAPS = True  # Save saliency maps for visualization

# Create global config instance
config = Config()

# Also export all config variables for backward compatibility with import *
PROJECT_ROOT = config.PROJECT_ROOT
DATA_ROOT = config.DATA_ROOT
RESULTS_DIR = config.RESULTS_DIR
LOGS_DIR = config.LOGS_DIR
ORIGINAL_CONTENT_DIR = config.ORIGINAL_CONTENT_DIR
TEST_IMAGES_DIR = config.TEST_IMAGES_DIR
SALIENCY_FREELOOK_DIR = config.SALIENCY_FREELOOK_DIR
SALIENCY_SCORING_DIR = config.SALIENCY_SCORING_DIR
NUM_CONTENTS = config.NUM_CONTENTS
NUM_LEVELS = config.NUM_LEVELS
NUM_IMAGES = config.NUM_IMAGES
COMPRESSION_LEVELS = config.COMPRESSION_LEVELS
SEED = config.SEED
VERBOSE = config.VERBOSE
EPSILON = config.EPSILON
SALIENCY_DENOISE_SIGMA = config.SALIENCY_DENOISE_SIGMA
IMAGE_RESIZE_METHOD = config.IMAGE_RESIZE_METHOD
LOCO_FOLD = config.LOCO_FOLD
ALPHA_DEFAULT = config.ALPHA_DEFAULT
BETA_DEFAULT = config.BETA_DEFAULT
GAMMA_DEFAULT = config.GAMMA_DEFAULT
W_FREELOOK_DEFAULT = config.W_FREELOOK_DEFAULT
W_ARTIFACT_DEFAULT = config.W_ARTIFACT_DEFAULT
W_CENTER_DEFAULT = config.W_CENTER_DEFAULT
COMPUTE_CC = config.COMPUTE_CC
COMPUTE_JSD = config.COMPUTE_JSD
COMPUTE_ENTROPY = config.COMPUTE_ENTROPY
COMPUTE_CENTROID_SHIFT = config.COMPUTE_CENTROID_SHIFT
SAVE_FIGURES = config.SAVE_FIGURES
SAVE_TABLES = config.SAVE_TABLES
SAVE_MAPS = config.SAVE_MAPS

print(f"Configuration loaded from {Path(__file__).name}")
print(f"Data root: {DATA_ROOT}")
print(f"Results dir: {RESULTS_DIR}")
