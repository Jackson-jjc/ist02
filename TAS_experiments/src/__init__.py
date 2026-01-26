"""
TAS Experiments Package
Task-Adaptive Saliency for Image Quality Assessment
"""

__version__ = '1.0.0'
__author__ = 'Research Team'

from . import config
from .data_loader import DataLoader
from .artifact_maps import ArtifactMapGenerator
from .tas_model import TASModel
from .metrics import SaliencyMetrics
from .visualizer import ResultsVisualizer

__all__ = [
    'config',
    'DataLoader',
    'ArtifactMapGenerator',
    'TASModel',
    'SaliencyMetrics',
    'ResultsVisualizer',
]
