"""
Multi-dataset support for TAS validation
Extends DataLoader to support multiple eye-tracking datasets

Supported datasets:
1. TUD (Task-based, 40 images, multiple compression levels)
2. JIST01 (Alternative dataset, if available)
"""
import os
import numpy as np
from pathlib import Path
from PIL import Image
import cv2
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MultiDatasetLoader:
    """Load data from multiple eye-tracking datasets"""
    
    def __init__(self, config):
        self.config = config
        self.datasets = {}
        self.image_cache = {}
        self.saliency_cache = {}
    
    def register_dataset(self, dataset_name: str, dataset_path: str,
                        data_type: str = 'unknown') -> bool:
        """
        Register a new dataset for loading
        
        Args:
            dataset_name: Name for this dataset (e.g., 'TUD', 'JIST01')
            dataset_path: Path to dataset root folder
            data_type: Dataset structure type ('tud', 'jist01', 'generic')
        
        Returns:
            True if successfully registered, False otherwise
        """
        dataset_path = Path(dataset_path)
        
        if not dataset_path.exists():
            logger.error(f"Dataset path does not exist: {dataset_path}")
            return False
        
        self.datasets[dataset_name] = {
            'path': dataset_path,
            'type': data_type,
            'num_images': 0,
            'num_contents': 0
        }
        
        logger.info(f"Registered dataset '{dataset_name}' at {dataset_path}")
        return True
    
    def analyze_jist01_structure(self, dataset_path: str) -> Dict:
        """
        Analyze JIST01 dataset structure
        
        Expected structure:
        /data/
            image/          → original images
            fixation/       → fixation points
            map/            → saliency maps
            fixation_img/   → fixation visualizations
        """
        dataset_path = Path(dataset_path)
        info = {
            'has_images': False,
            'has_fixations': False,
            'has_maps': False,
            'num_images': 0,
            'image_filenames': []
        }
        
        # Check for image folder
        image_dir = dataset_path / 'image'
        if image_dir.exists():
            info['has_images'] = True
            image_files = list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.png'))
            info['num_images'] = len(image_files)
            info['image_filenames'] = [f.name for f in image_files]
            logger.info(f"Found {len(image_files)} images in JIST01 dataset")
        
        # Check for fixation folder
        fixation_dir = dataset_path / 'fixation'
        if fixation_dir.exists():
            info['has_fixations'] = True
            logger.info(f"Found fixation data in JIST01 dataset")
        
        # Check for saliency maps folder
        map_dir = dataset_path / 'map'
        if map_dir.exists():
            info['has_maps'] = True
            logger.info(f"Found saliency maps in JIST01 dataset")
        
        return info
    
    def load_jist01_image(self, dataset_path: str, filename: str) -> Optional[np.ndarray]:
        """Load image from JIST01 dataset"""
        dataset_path = Path(dataset_path)
        image_path = dataset_path / 'image' / filename
        
        if not image_path.exists():
            logger.warning(f"Image not found: {image_path}")
            return None
        
        try:
            img = Image.open(image_path)
            img_array = np.array(img, dtype=np.float32)
            return img_array
        except Exception as e:
            logger.error(f"Failed to load image {filename}: {e}")
            return None
    
    def load_jist01_fixations(self, dataset_path: str, filename_stem: str) -> Optional[np.ndarray]:
        """
        Load fixation map from JIST01 dataset
        
        Expected format: .npy or .mat files with fixation coordinates/density
        """
        dataset_path = Path(dataset_path)
        fixation_dir = dataset_path / 'fixation'
        
        # Try different file formats
        for ext in ['.npy', '.mat', '.txt']:
            fixation_path = fixation_dir / (filename_stem + ext)
            if fixation_path.exists():
                try:
                    if ext == '.npy':
                        fixation_map = np.load(fixation_path)
                        return fixation_map
                    else:
                        logger.warning(f"Format {ext} not yet supported for fixations")
                except Exception as e:
                    logger.error(f"Failed to load fixation {fixation_path}: {e}")
        
        return None
    
    def load_jist01_saliency_map(self, dataset_path: str, filename_stem: str) -> Optional[np.ndarray]:
        """
        Load saliency map from JIST01 dataset
        """
        dataset_path = Path(dataset_path)
        map_dir = dataset_path / 'map'
        
        # Try different file formats
        for ext in ['.npy', '.png', '.jpg']:
            map_path = map_dir / (filename_stem + ext)
            if map_path.exists():
                try:
                    if ext == '.npy':
                        saliency = np.load(map_path)
                        return saliency
                    else:
                        img = Image.open(map_path)
                        saliency = np.array(img, dtype=np.float32)
                        # Normalize to [0, 1]
                        if saliency.max() > 1:
                            saliency = saliency / 255.0
                        return saliency
                except Exception as e:
                    logger.error(f"Failed to load saliency map {map_path}: {e}")
        
        return None
    
    def create_synthetic_jist01_samples(self, dataset_path: str,
                                       num_compression_levels: int = 4) -> Dict:
        """
        Create TAS-compatible samples from JIST01 dataset
        
        Since JIST01 doesn't have compression levels, create them synthetically
        by applying JPEG compression at different quality levels
        
        Returns:
            Dictionary mapping content_id -> {original, compressed_levels, saliency}
        """
        dataset_path = Path(dataset_path)
        info = self.analyze_jist01_structure(str(dataset_path))
        
        if not info['has_images']:
            logger.error("No images found in JIST01 dataset")
            return {}
        
        samples = {}
        quality_levels = [10, 30, 50, 70][:num_compression_levels]
        
        for idx, image_filename in enumerate(info['image_filenames']):
            filename_stem = image_filename.rsplit('.', 1)[0]
            
            # Load original image
            original = self.load_jist01_image(str(dataset_path), image_filename)
            if original is None:
                continue
            
            # Create compressed versions
            compressed_versions = {}
            for quality in quality_levels:
                # Save to temp file and reload (simulating JPEG compression)
                temp_path = f"/tmp/jist01_temp_q{quality}.jpg"
                try:
                    pil_img = Image.fromarray(original.astype(np.uint8))
                    pil_img.save(temp_path, 'JPEG', quality=quality)
                    compressed = np.array(Image.open(temp_path), dtype=np.float32)
                    compressed_versions[quality] = compressed
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to create compressed version for {filename_stem} at Q{quality}: {e}")
            
            if len(compressed_versions) == 0:
                continue
            
            # Load saliency map if available
            saliency = self.load_jist01_saliency_map(str(dataset_path), filename_stem)
            
            samples[filename_stem] = {
                'original': original,
                'compressed': compressed_versions,
                'saliency': saliency,
                'source': 'jist01'
            }
        
        logger.info(f"Created {len(samples)} samples from JIST01 dataset with synthetic compression")
        return samples
    
    def create_compatible_sample_pairs(self, tud_data: Dict,
                                       jist01_data: Dict) -> List[Dict]:
        """
        Create compatible sample pairs for multi-dataset evaluation
        
        Ensures both datasets have same structure for fair comparison
        """
        pairs = []
        
        # TUD samples
        for content_id, tud_sample in tud_data.items():
            pairs.append({
                'content_id': f"TUD_{content_id}",
                'original': tud_sample['original'],
                'compressed': tud_sample['compressed'],
                'saliency': tud_sample['saliency'],
                'source': 'TUD'
            })
        
        # JIST01 samples
        for content_id, jist_sample in jist01_data.items():
            pairs.append({
                'content_id': f"JIST01_{content_id}",
                'original': jist_sample['original'],
                'compressed': jist_sample['compressed'],
                'saliency': jist_sample['saliency'],
                'source': 'JIST01'
            })
        
        logger.info(f"Created {len(pairs)} sample pairs for cross-dataset evaluation")
        return pairs
