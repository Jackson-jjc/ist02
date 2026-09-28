"""Configuration for the SC-TAS experiments.

Dataset paths are configured through environment variables so that the public
repository does not depend on the authors' cluster filesystem.
"""
import os
from pathlib import Path


def _path_from_env(name: str, default: Path) -> Path:
    """Return an expanded absolute path from an environment variable."""
    value = os.environ.get(name)
    path = Path(value).expanduser() if value else default
    return path.resolve()


class Config:
    """Configuration class for TAS experiments"""
    def __init__(self):
        # Base paths
        self.PROJECT_ROOT = Path(__file__).resolve().parent.parent
        repository_root = self.PROJECT_ROOT.parent

        # Public, portable defaults. Override these paths when the datasets are
        # stored elsewhere (see the repository README).
        self.DATA_ROOT = _path_from_env(
            'SCTAS_R2_ROOT', repository_root / 'TUD_Task_EyeTracking')
        self.R1_ROOT = _path_from_env(
            'SCTAS_R1_ROOT',
            repository_root / 'TUD_LIVE_EyeTracking' / 'TUD_LIVE_EyeTracking')
        self.INT_ROOT = _path_from_env(
            'SCTAS_INT_ROOT', repository_root / 'TUD_Interactions')
        self.RESULTS_DIR = _path_from_env(
            'SCTAS_RESULTS_ROOT', self.PROJECT_ROOT / 'results')
        self.LOGS_DIR = self.RESULTS_DIR / 'logs'

        # Data folders
        self.ORIGINAL_CONTENT_DIR = self.DATA_ROOT / 'OriginalContent'
        self.TEST_IMAGES_DIR = self.DATA_ROOT / 'TestImages'
        self.SALIENCY_FREELOOK_DIR = self.DATA_ROOT / 'SaliencyFreeLook'
        self.SALIENCY_SCORING_DIR = self.DATA_ROOT / 'SaliencyScoring'

        # Create output directories
        self.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Preprocessing
        self.EPSILON = 1e-12
        self.SALIENCY_DENOISE_SIGMA = 1.0

# Create global config instance
config = Config()

# Also export all config variables for backward compatibility with import *
PROJECT_ROOT = config.PROJECT_ROOT
DATA_ROOT = config.DATA_ROOT
R1_ROOT = config.R1_ROOT
INT_ROOT = config.INT_ROOT
RESULTS_DIR = config.RESULTS_DIR
LOGS_DIR = config.LOGS_DIR
ORIGINAL_CONTENT_DIR = config.ORIGINAL_CONTENT_DIR
TEST_IMAGES_DIR = config.TEST_IMAGES_DIR
SALIENCY_FREELOOK_DIR = config.SALIENCY_FREELOOK_DIR
SALIENCY_SCORING_DIR = config.SALIENCY_SCORING_DIR
EPSILON = config.EPSILON
SALIENCY_DENOISE_SIGMA = config.SALIENCY_DENOISE_SIGMA


if __name__ == '__main__':
    print(f"R2 root: {DATA_ROOT}")
    print(f"R1 root: {R1_ROOT}")
    print(f"INT root: {INT_ROOT}")
    print(f"Results root: {RESULTS_DIR}")
