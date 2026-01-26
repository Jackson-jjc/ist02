"""
Improved artifact detection for TAS v2
Enhanced multi-method approach: SSIM + DCT + Blockiness + Ringing + CSF weighting

Improvement targets:
- artifact_cc: 0.074 → 0.35+ (47x improvement)
- Method: Combine spatial, frequency, and perceptual artifacts
"""
import numpy as np
import cv2
from typing import Tuple, Optional, Dict
import logging
from scipy import signal
from scipy.fftpack import dctn

logger = logging.getLogger(__name__)


class ImprovedArtifactDetector:
    """Enhanced artifact detection combining multiple methods"""
    
    def __init__(self, config=None):
        self.config = config
        self.epsilon = 1e-12
        self.method_weights = {
            'ssim': 0.35,
            'blockiness': 0.25,
            'ringing': 0.20,
            'dct': 0.20
        }
    
    # ============== Component 1: Multi-scale SSIM ==============
    
    def _compute_ssim_local(self, img_ref: np.ndarray, 
                           img_dist: np.ndarray,
                           win_size: int = 11,
                           sigma: float = 1.5,
                           k1: float = 0.01,
                           k2: float = 0.03) -> np.ndarray:
        """Compute local SSIM map (spatial SSIM)"""
        # Ensure grayscale
        if len(img_ref.shape) == 3:
            ref = cv2.cvtColor(img_ref.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
            dist = cv2.cvtColor(img_dist.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            ref = img_ref.astype(np.float32)
            dist = img_dist.astype(np.float32)
        
        # Normalize to [0, 1]
        ref = ref / 255.0 if ref.max() > 1 else ref
        dist = dist / 255.0 if dist.max() > 1 else dist
        
        # Create Gaussian window
        window = cv2.getGaussianKernel(win_size, sigma)
        window = window @ window.T
        
        c1 = (k1 * 255) ** 2
        c2 = (k2 * 255) ** 2
        
        # Compute SSIM
        mu1 = cv2.filter2D(ref, -1, window)
        mu2 = cv2.filter2D(dist, -1, window)
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2
        
        sigma1_sq = cv2.filter2D(ref ** 2, -1, window) - mu1_sq
        sigma2_sq = cv2.filter2D(dist ** 2, -1, window) - mu2_sq
        sigma12 = cv2.filter2D(ref * dist, -1, window) - mu1_mu2
        
        ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / \
                   ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))
        
        return np.clip(ssim_map, -1, 1)
    
    def compute_ssim_artifact(self, img_ref: np.ndarray,
                             img_dist: np.ndarray) -> np.ndarray:
        """SSIM-based artifact: 1 - SSIM (lower SSIM = more artifact)"""
        ssim_map = self._compute_ssim_local(img_ref, img_dist)
        artifact = 1.0 - ssim_map  # Invert: higher = more artifact
        return np.clip(artifact, 0, 1)
    
    # ============== Component 2: Blockiness Detection ==============
    
    def compute_blockiness_artifact(self, img_dist: np.ndarray,
                                   block_size: int = 8) -> np.ndarray:
        """
        JPEG blockiness detection: horizontal and vertical gradient peaks at block boundaries
        """
        # Extract luminance
        if len(img_dist.shape) == 3:
            lum = cv2.cvtColor(img_dist.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            lum = img_dist.astype(np.float32)
        
        h, w = lum.shape
        blockiness = np.zeros((h, w), dtype=np.float32)
        
        # Compute horizontal and vertical differences
        diff_h = np.abs(np.diff(lum.astype(np.float32), axis=0))
        diff_v = np.abs(np.diff(lum.astype(np.float32), axis=1))
        
        # Pad back to original size
        diff_h = np.pad(diff_h, ((0, 1), (0, 0)), mode='edge')
        diff_v = np.pad(diff_v, ((0, 0), (0, 1)), mode='edge')
        
        # Enhance at block boundaries (every 8 pixels)
        for y in range(0, h, block_size):
            if y > 0 and y < h:
                blockiness[y, :] += diff_h[y, :] * 2.0
        
        for x in range(0, w, block_size):
            if x > 0 and x < w:
                blockiness[:, x] += diff_v[:, x] * 2.0
        
        # Smooth
        blockiness = cv2.GaussianBlur(blockiness, (5, 5), 1.0)
        
        # Normalize
        if blockiness.max() > 0:
            blockiness = blockiness / np.percentile(blockiness, 95)
        
        return np.clip(blockiness, 0, 1)
    
    # ============== Component 3: Ringing Detection ==============
    
    def compute_ringing_artifact(self, img_dist: np.ndarray) -> np.ndarray:
        """
        Ringing artifacts: oscillations near edges
        Detected by high-frequency components near edge regions
        """
        # Extract luminance
        if len(img_dist.shape) == 3:
            lum = cv2.cvtColor(img_dist.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            lum = img_dist.astype(np.float32)
        
        # Edge detection
        edges = cv2.Canny(lum.astype(np.uint8), 50, 150)
        
        # High-frequency components (Laplacian)
        laplacian = cv2.Laplacian(lum, cv2.CV_32F)
        high_freq = np.abs(laplacian)
        
        # Dilate edges to create band around edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        edge_band = cv2.dilate(edges, kernel, iterations=2).astype(np.float32) / 255.0
        
        # Ringing is high-frequency energy in edge regions
        ringing = high_freq * edge_band
        
        # Smooth
        ringing = cv2.GaussianBlur(ringing, (3, 3), 1.0)
        
        # Normalize
        if ringing.max() > 0:
            ringing = ringing / np.percentile(ringing, 95)
        
        return np.clip(ringing, 0, 1)
    
    # ============== Component 4: DCT Artifact ==============
    
    def compute_dct_artifact(self, img_dist: np.ndarray,
                            block_size: int = 8) -> np.ndarray:
        """
        DCT-based JPEG artifact detection
        High-frequency accumulation indicates compression distortion
        """
        # Extract luminance
        if len(img_dist.shape) == 3:
            lum = cv2.cvtColor(img_dist.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            lum = img_dist.astype(np.float32)
        
        h, w = lum.shape
        dct_artifact = np.zeros((h, w), dtype=np.float32)
        
        # Process each JPEG block
        for y in range(0, h - block_size + 1, block_size):
            for x in range(0, w - block_size + 1, block_size):
                block = lum[y:y+block_size, x:x+block_size]
                
                # DCT
                dct_block = cv2.dct(block / 255.0)
                
                # High-frequency energy (outer ring, excluding DC and low-freq)
                hf = np.abs(dct_block)
                hf[0, 0] = 0  # Remove DC
                hf[0:3, 0:3] = 0  # Remove low-freq
                
                hf_energy = np.sum(hf ** 2)
                dct_artifact[y:y+block_size, x:x+block_size] = hf_energy
        
        # Smooth
        dct_artifact = cv2.GaussianBlur(dct_artifact, (5, 5), 1.0)
        
        # Normalize
        if dct_artifact.max() > 0:
            dct_artifact = dct_artifact / np.percentile(dct_artifact, 95)
        
        return np.clip(dct_artifact, 0, 1)
    
    # ============== Component 5: CSF Weighting ==============
    
    def compute_csf_weights(self, shape: Tuple[int, int]) -> np.ndarray:
        """
        Contrast Sensitivity Function (CSF) weights
        Human eye is more sensitive to artifacts in mid-frequency regions
        """
        h, w = shape
        
        # Create frequency grid
        y_freq = np.fft.fftfreq(h)[:, np.newaxis]
        x_freq = np.fft.fftfreq(w)[np.newaxis, :]
        freq = np.sqrt(y_freq**2 + x_freq**2)
        
        # CSF: peaks at mid-frequencies (2-8 cycles per degree)
        # Simplified model: Gaussian-like sensitivity
        csf = np.exp(-((freq - 0.05) ** 2) / (2 * (0.03 ** 2)))
        
        return csf / (csf.max() + self.epsilon)
    
    # ============== Main Method: Combined Artifact Detection ==============
    
    def compute_artifact_map(self, img_reference: np.ndarray,
                            img_distorted: np.ndarray,
                            method: str = 'combined') -> Dict[str, np.ndarray]:
        """
        Compute artifact map using improved multi-method approach
        
        Args:
            img_reference: Reference image
            img_distorted: Distorted image
            method: 'combined' (default) or individual: 'ssim', 'blockiness', 'ringing', 'dct'
        
        Returns:
            Dictionary with individual maps and combined artifact map
        """
        maps = {}
        
        # Compute individual components
        maps['ssim'] = self.compute_ssim_artifact(img_reference, img_distorted)
        maps['blockiness'] = self.compute_blockiness_artifact(img_distorted)
        maps['ringing'] = self.compute_ringing_artifact(img_distorted)
        maps['dct'] = self.compute_dct_artifact(img_distorted)
        
        if method == 'combined':
            # Weighted combination
            artifact = (
                self.method_weights['ssim'] * maps['ssim'] +
                self.method_weights['blockiness'] * maps['blockiness'] +
                self.method_weights['ringing'] * maps['ringing'] +
                self.method_weights['dct'] * maps['dct']
            )
            
            # Apply CSF weighting
            csf = self.compute_csf_weights(img_distorted.shape[:2])
            artifact = artifact * csf
            
            # Normalize
            if artifact.max() > 0:
                artifact = artifact / artifact.max()
            
            maps['combined'] = np.clip(artifact, 0, 1)
            return maps
        
        else:
            return maps
    
    def set_method_weights(self, weights: Dict[str, float]):
        """Update method weights"""
        total = sum(weights.values())
        self.method_weights = {k: v / total for k, v in weights.items()}
        logger.info(f"Updated artifact detection weights: {self.method_weights}")
