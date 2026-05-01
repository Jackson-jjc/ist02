"""
Artifact map computation (FR-Artifact and NR-Artifact)
Improved version with multi-scale SSIM + DCT + CSF weighting
"""
import numpy as np
import cv2
from typing import Tuple, Optional
import logging
from scipy import signal
from scipy.fftpack import dctn, idctn

logger = logging.getLogger(__name__)

class ArtifactMapGenerator:
    """Generate artifact maps for JPEG distortion"""
    
    def __init__(self, config=None):
        self.config = config
        # CSF (Contrast Sensitivity Function) parameters for human vision
        self.csf_frequencies = np.linspace(0.1, 20, 20)
        self.csf_sensitivity = self._get_csf_lookup()
    
    def _get_csf_lookup(self) -> np.ndarray:
        """
        Contrast Sensitivity Function (Barten's model adapted for perception)
        Higher sensitivity at mid-frequencies (2-8 cpd), lower at very high/low
        """
        # Normalized CSF: peaks around 4 cpd
        freq = np.linspace(0.1, 20, 100)
        # Simplified CSF model
        csf = 2.6 * (0.0192 + 0.114 * freq) * np.exp(-(0.114 * freq) ** 1.1)
        return csf / np.max(csf)  # Normalize to [0, 1]

    @staticmethod
    def _normalize_unit_range(arr: np.ndarray) -> np.ndarray:
        """Normalize a non-negative map to [0, 1] without changing its shape."""
        arr = np.maximum(arr, 0).astype(np.float32)
        max_val = float(np.max(arr))
        if max_val > 0:
            arr = arr / max_val
        return np.clip(arr, 0, 1)
    
    def _compute_ssim_multiscale(self, img_ref: np.ndarray, 
                                 img_dist: np.ndarray,
                                 win_size: int = 11,
                                 sigma: float = 1.5,
                                 num_scales: int = 5,
                                 k1: float = 0.01,
                                 k2: float = 0.03) -> Tuple[float, np.ndarray]:
        """
        Compute multi-scale SSIM with weights emphasizing perceptual importance.
        
        Returns:
            (mssim: multi-scale SSIM score, ssim_map: spatial SSIM map)
        """
        # Ensure grayscale
        if len(img_ref.shape) == 3:
            # Convert RGB/YCrCb to grayscale
            if img_ref.shape[2] == 3:
                ref = cv2.cvtColor(img_ref.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
                dist = cv2.cvtColor(img_dist.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
            else:
                ref = img_ref[:, :, 0].astype(np.float32)
                dist = img_dist[:, :, 0].astype(np.float32)
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
        
        # Multi-scale SSIM with weights: later scales matter less
        mssim_scores = []
        ssim_maps = []
        scales_weights = [0.0448, 0.2856, 0.3001, 0.2363, 0.0333]  # Per literature
        
        img_r = ref.copy()
        img_d = dist.copy()
        
        for scale_idx in range(num_scales):
            # Compute single-scale SSIM
            mu1 = cv2.filter2D(img_r, -1, window)
            mu2 = cv2.filter2D(img_d, -1, window)
            mu1_sq = mu1 ** 2
            mu2_sq = mu2 ** 2
            mu1_mu2 = mu1 * mu2
            
            sigma1_sq = cv2.filter2D(img_r ** 2, -1, window) - mu1_sq
            sigma2_sq = cv2.filter2D(img_d ** 2, -1, window) - mu2_sq
            sigma12 = cv2.filter2D(img_r * img_d, -1, window) - mu1_mu2
            
            ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / \
                      ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))
            
            ssim_map = np.clip(ssim_map, -1, 1)
            ssim_maps.append(ssim_map)
            
            mssim_scores.append(np.mean(ssim_map))
            
            # Downsample for next scale
            if scale_idx < num_scales - 1:
                img_r = cv2.pyrDown(img_r)
                img_d = cv2.pyrDown(img_d)
        
        # Compute weighted multi-scale SSIM
        mssim = np.prod(np.array(mssim_scores) ** np.array(scales_weights))
        
        # Use first-scale SSIM map (highest resolution)
        return mssim, ssim_maps[0]
    
    def _compute_dct_artifact(self, img_dist: np.ndarray,
                             block_size: int = 8) -> np.ndarray:
        """
        Detect JPEG artifacts using DCT coefficient analysis.
        High-frequency accumulation in DCT blocks indicates compression.
        
        Returns:
            DCT artifact map [0, 1]
        """
        # Extract luminance
        if len(img_dist.shape) == 3:
            lum = cv2.cvtColor(img_dist.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            lum = img_dist.astype(np.float32)
        
        h, w = lum.shape
        dct_artifact = np.zeros((h, w), dtype=np.float32)
        
        # Process each 8×8 JPEG block
        for y in range(0, h - block_size + 1, block_size):
            for x in range(0, w - block_size + 1, block_size):
                block = lum[y:y+block_size, x:x+block_size]
                
                # Compute DCT
                dct_block = cv2.dct(block)
                
                # Extract high-frequency components (outer ring of DCT)
                # JPEG compression typically zeros out high frequencies
                high_freq = np.abs(dct_block)
                high_freq[0, 0] = 0  # Remove DC component
                high_freq[0:3, 0:3] = 0  # Remove low-freq components
                
                # Compute high-frequency energy
                hf_energy = np.sum(high_freq ** 2)
                dct_artifact[y:y+block_size, x:x+block_size] = hf_energy
        
        # Normalize
        if dct_artifact.max() > 0:
            dct_artifact = dct_artifact / np.percentile(dct_artifact, 95)
            dct_artifact = np.clip(dct_artifact, 0, 1)
        
        # Smooth to create continuous map
        dct_artifact = cv2.GaussianBlur(dct_artifact, (5, 5), 1.0)
        
        return dct_artifact
    
    def compute_fr_artifact(self, img_reference: np.ndarray, 
                           img_distorted: np.ndarray,
                           use_luminance: bool = True,
                           use_ssim: bool = True,
                           use_dct: bool = True,
                           ssim_weight: float = 0.6,
                           dct_weight: float = 0.4) -> np.ndarray:
        """
        Compute full-reference artifact map using multi-scale SSIM + DCT analysis.
        
        This improved method combines:
        - Multi-scale SSIM (perceptual quality metric)
        - DCT coefficient analysis (direct JPEG artifact detection)
        - CSF weighting (human vision sensitivity)
        
        Args:
            img_reference: Reference image (H, W, C) or (H, W)
            img_distorted: Distorted image (H, W, C) or (H, W)
            use_luminance: Use Y channel if True
            use_ssim: Include multi-scale SSIM component
            use_dct: Include DCT artifact component
            ssim_weight: Weight for SSIM (default: 0.6)
            dct_weight: Weight for DCT (default: 0.4)
        
        Returns:
            Artifact map A_FR normalized to [0, 1]
        """
        artifact_map = np.zeros_like(img_distorted[:, :, 0] if len(img_distorted.shape) == 3 
                                    else img_distorted, dtype=np.float32)
        
        # Component 1: Multi-scale SSIM (lower SSIM = more artifact)
        if use_ssim:
            mssim, ssim_map = self._compute_ssim_multiscale(img_reference, img_distorted)
            # Convert SSIM to artifact measure (inverted): 1 - SSIM
            ssim_artifact = 1.0 - np.clip(ssim_map, -1, 1)
            artifact_map += ssim_weight * ssim_artifact
            logger.debug(f"FR-Artifact SSIM component: mssim={mssim:.4f}, mean_artifact={np.mean(ssim_artifact):.4f}")
        
        # Component 2: DCT-based artifact detection
        if use_dct:
            dct_artifact = self._compute_dct_artifact(img_distorted)
            artifact_map += dct_weight * dct_artifact
            logger.debug(f"FR-Artifact DCT component: mean_artifact={np.mean(dct_artifact):.4f}")
        
        # Normalize to [0, 1]
        if artifact_map.max() > 0:
            artifact_map = artifact_map / artifact_map.max()
        
        artifact_map = np.clip(artifact_map, 0, 1)
        
        return artifact_map
    
    def compute_blockiness_map(self, img_distorted: np.ndarray,
                              use_luminance: bool = True,
                              block_size: int = 8) -> np.ndarray:
        """
        Compute blockiness artifact map based on 8×8 JPEG block boundaries.
        
        Args:
            img_distorted: Distorted image
            use_luminance: Use Y channel if True
            block_size: JPEG block size (8 for standard JPEG)
        
        Returns:
            Blockiness map normalized to [0, 1]
        """
        # Extract luminance
        if len(img_distorted.shape) == 3:
            if use_luminance:
                lum = img_distorted[:, :, 0]
            else:
                lum = cv2.cvtColor(img_distorted.astype(np.uint8), 
                                  cv2.COLOR_YCrCb2GRAY).astype(np.float32)
        else:
            lum = img_distorted
        
        h, w = lum.shape
        blockiness = np.zeros((h, w), dtype=np.float32)
        
        # Compute horizontal and vertical differences
        diff_h = np.abs(np.diff(lum, axis=0))
        diff_v = np.abs(np.diff(lum, axis=1))
        
        # Pad differences back to original size
        diff_h = np.pad(diff_h, ((0, 1), (0, 0)), mode='edge')
        diff_v = np.pad(diff_v, ((0, 0), (0, 1)), mode='edge')
        
        # Enhance differences at block boundaries
        # Horizontal boundaries (every 8 pixels)
        for y in range(0, h, block_size):
            if y > 0 and y < h:
                blockiness[y, :] += diff_h[y, :] * 2.0
        
        # Vertical boundaries (every 8 pixels)
        for x in range(0, w, block_size):
            if x > 0 and x < w:
                blockiness[:, x] += diff_v[:, x] * 2.0
        
        # Smooth blockiness map with Gaussian filter
        blockiness = cv2.GaussianBlur(blockiness, (5, 5), 1.0)
        
        # Normalize to [0, 1]
        if blockiness.max() > 0:
            blockiness = blockiness / blockiness.max()
        
        return blockiness
    
    def compute_ringing_map(self, img_distorted: np.ndarray,
                           use_luminance: bool = True) -> np.ndarray:
        """
        Compute ringing artifacts near edges (oscillations around edges).
        
        Args:
            img_distorted: Distorted image
            use_luminance: Use Y channel if True
        
        Returns:
            Ringing map normalized to [0, 1]
        """
        # Extract luminance
        if len(img_distorted.shape) == 3:
            if use_luminance:
                lum = img_distorted[:, :, 0]
            else:
                lum = cv2.cvtColor(img_distorted.astype(np.uint8), 
                                  cv2.COLOR_YCrCb2GRAY).astype(np.float32)
        else:
            lum = img_distorted
        
        # Detect edges using Canny
        edges = cv2.Canny(lum.astype(np.uint8), 50, 150)
        
        # Compute high-frequency components near edges
        laplacian = cv2.Laplacian(lum, cv2.CV_32F)
        high_freq = np.abs(laplacian)
        
        # Create band around edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        edge_band = cv2.dilate(edges, kernel, iterations=2)
        
        # Extract high-frequency energy in edge band
        ringing = high_freq * (edge_band.astype(np.float32) / 255.0)
        
        # Smooth
        ringing = cv2.GaussianBlur(ringing, (3, 3), 1.0)
        
        # Normalize to [0, 1]
        if ringing.max() > 0:
            ringing = ringing / ringing.max()
        
        return ringing
    
    def compute_nr_artifact(self, img_distorted: np.ndarray,
                           use_blockiness: bool = True,
                           use_dct: bool = True,
                           use_ringing: bool = True,
                           blockiness_weight: float = 0.4,
                           dct_weight: float = 0.4,
                           ringing_weight: float = 0.2) -> np.ndarray:
        """
        Compute no-reference artifact map using multiple detection methods.
        
        Improved version combines:
        - DCT-based blockiness (0.4 weight) - most reliable for JPEG
        - High-frequency analysis (0.4 weight) - general compression artifacts
        - Ringing detection (0.2 weight) - edge artifacts
        
        Args:
            img_distorted: Distorted image
            use_blockiness: Include improved blockiness detection
            use_dct: Include DCT artifact component
            use_ringing: Include ringing detection
            blockiness_weight: Weight for blockiness
            dct_weight: Weight for DCT
            ringing_weight: Weight for ringing
        
        Returns:
            NR artifact map normalized to [0, 1]
        """
        components = self.compute_nr_artifact_components(
            img_distorted,
            blockiness_weight=blockiness_weight,
            dct_weight=dct_weight,
            ringing_weight=ringing_weight,
        )

        artifact_nr = np.zeros_like(components['combined'])
        if use_blockiness:
            artifact_nr += blockiness_weight * components['blockiness']
            logger.debug(f"NR-Artifact blockiness: mean={np.mean(components['blockiness']):.4f}")
        if use_dct:
            artifact_nr += dct_weight * components['dct']
            logger.debug(f"NR-Artifact DCT: mean={np.mean(components['dct']):.4f}")
        if use_ringing:
            artifact_nr += ringing_weight * components['ringing']
            logger.debug(f"NR-Artifact ringing: mean={np.mean(components['ringing']):.4f}")

        return self._normalize_unit_range(artifact_nr)

    def compute_nr_artifact_components(self, img_distorted: np.ndarray,
                                      blockiness_weight: float = 0.4,
                                      dct_weight: float = 0.4,
                                      ringing_weight: float = 0.2) -> dict:
        """
        Compute the three NR artifact sub-components and their weighted fusion.

        Returns:
            Dict with normalized component maps in [0, 1]:
                blockiness, dct, ringing, combined
        """
        blockiness = self._normalize_unit_range(self._compute_improved_blockiness(img_distorted))
        dct_artifact = self._normalize_unit_range(self._compute_dct_artifact(img_distorted))
        ringing = self._normalize_unit_range(self.compute_ringing_map(img_distorted, use_luminance=True))

        combined = (
            blockiness_weight * blockiness +
            dct_weight * dct_artifact +
            ringing_weight * ringing
        )

        return {
            'blockiness': blockiness,
            'dct': dct_artifact,
            'ringing': ringing,
            'combined': self._normalize_unit_range(combined),
        }
    
    def _compute_improved_blockiness(self, img_distorted: np.ndarray,
                                    use_luminance: bool = True,
                                    block_size: int = 8) -> np.ndarray:
        """
        Improved blockiness detection using DCT information.
        
        Instead of just edge detection, analyze DCT coefficients
        at block boundaries to detect compression artifacts.
        """
        # Extract luminance
        if len(img_distorted.shape) == 3:
            lum = cv2.cvtColor(img_distorted.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            lum = img_distorted.astype(np.float32)
        
        h, w = lum.shape
        blockiness = np.zeros((h, w), dtype=np.float32)
        
        # Compute differences across and along block boundaries
        for y in range(0, h - block_size + 1, block_size):
            for x in range(0, w - block_size + 1, block_size):
                # Horizontal boundary differences
                if x + block_size < w:
                    left_col = lum[y:y+block_size, x+block_size-1]
                    right_col = lum[y:y+block_size, x+block_size]
                    h_diff = np.abs(left_col - right_col)
                    blockiness[y:y+block_size, x+block_size-1:x+block_size+1] += h_diff[:, np.newaxis] * 0.5
                
                # Vertical boundary differences
                if y + block_size < h:
                    top_row = lum[y+block_size-1, x:x+block_size]
                    bot_row = lum[y+block_size, x:x+block_size]
                    v_diff = np.abs(top_row - bot_row)
                    blockiness[y+block_size-1:y+block_size+1, x:x+block_size] += v_diff[np.newaxis, :] * 0.5
        
        # Enhance and smooth
        blockiness = cv2.GaussianBlur(blockiness, (5, 5), 1.0)
        
        # Normalize
        if blockiness.max() > 0:
            blockiness = blockiness / blockiness.max()
        
        return blockiness
    
    def normalize_artifact_to_probability(self, artifact_map: np.ndarray) -> np.ndarray:
        """
        Convert artifact map to probability distribution.
        
        Args:
            artifact_map: Artifact map
        
        Returns:
            Probability map that sums to 1
        """
        # Ensure non-negative
        artifact_map = np.maximum(artifact_map, 0)
        
        # Normalize
        total = np.sum(artifact_map) + 1e-12
        prob_map = artifact_map / total
        
        return prob_map


if __name__ == '__main__':
    print("Artifact map module loaded")
