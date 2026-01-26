"""
Data loading and preprocessing for TAS experiments
"""
import os
import re
import numpy as np
from pathlib import Path
from PIL import Image
import cv2
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """Load and preprocess image and saliency data"""
    
    def __init__(self, config):
        self.config = config
        self.image_cache = {}
        self.saliency_cache = {}
        
    def extract_content_and_level(self, filename: str) -> Tuple[str, int]:
        """
        Extract content name and compression level from filename.
        Format: {content_name}_jpgq_({level}).jpg
        """
        match = re.match(r'(.+)_jpgq_\((\d+)\)', filename.replace('.jpg', ''))
        if match:
            content_name = match.group(1)
            level = int(match.group(2))
            return content_name, level
        raise ValueError(f"Cannot parse filename: {filename}")
    
    def get_unique_contents(self) -> List[str]:
        """Get list of unique content names (40 contents)"""
        contents = set()
        for filename in os.listdir(self.config.TEST_IMAGES_DIR):
            if filename.endswith('.jpg'):
                content, _ = self.extract_content_and_level(filename)
                contents.add(content)
        return sorted(list(contents))
    
    def get_compression_levels(self, content_name: str) -> List[int]:
        """Get all compression levels for a given content"""
        levels = []
        for filename in os.listdir(self.config.TEST_IMAGES_DIR):
            if filename.endswith('.jpg'):
                extracted_content, level = self.extract_content_and_level(filename)
                if extracted_content == content_name:
                    levels.append(level)
        return sorted(list(set(levels)))
    
    def load_image(self, filename: str, color_space: str = 'ycrcb') -> np.ndarray:
        """
        Load image and convert to specified color space.
        Args:
            filename: Image filename
            color_space: 'ycrcb' (default for JPEG artifacts), 'rgb', or 'gray'
        Returns:
            Image array
        """
        if filename in self.image_cache:
            return self.image_cache[filename]
        
        filepath = self.config.TEST_IMAGES_DIR / filename
        img = Image.open(filepath)
        img_array = np.array(img, dtype=np.float32)
        
        if color_space == 'ycrcb':
            # Convert RGB to YCrCb (JPEG uses YCbCr which is similar)
            img_bgr = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2BGR)
            img_ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb).astype(np.float32)
            result = img_ycrcb
        elif color_space == 'gray':
            result = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:  # rgb
            result = img_array
        
        self.image_cache[filename] = result
        return result
    
    def load_original_image(self, content_name: str, color_space: str = 'ycrcb') -> Optional[np.ndarray]:
        """
        Load original reference image from OriginalContent folder.
        Supports both .bmp and .jpg formats.
        Args:
            content_name: Content name (e.g., 'arab_mountain')
            color_space: 'ycrcb' (default), 'rgb', or 'gray'
        Returns:
            Image array or None if not found
        """
        cache_key = f"original_{content_name}_{color_space}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        
        # Try different file extensions
        for ext in ['.bmp', '.jpg', '.png']:
            filepath = self.config.ORIGINAL_CONTENT_DIR / (content_name + ext)
            if filepath.exists():
                try:
                    img = Image.open(filepath)
                    img_array = np.array(img, dtype=np.float32)
                    
                    if color_space == 'ycrcb':
                        img_bgr = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2BGR)
                        img_ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb).astype(np.float32)
                        result = img_ycrcb
                    elif color_space == 'gray':
                        result = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
                    else:  # rgb
                        result = img_array
                    
                    self.image_cache[cache_key] = result
                    return result
                except Exception as e:
                    logger.warning(f"Failed to load original image {content_name}{ext}: {e}")
                    continue
        
        logger.warning(f"Original image not found for content: {content_name}")
        return None
    
    def load_saliency_map(self, filename: str, dataset_type: str = 'freelook') -> np.ndarray:
        """
        Load saliency map.
        Args:
            filename: Saliency map filename
            dataset_type: 'freelook' or 'scoring'
        Returns:
            Saliency map array
        """
        cache_key = f"{dataset_type}_{filename}"
        if cache_key in self.saliency_cache:
            return self.saliency_cache[cache_key]
        
        if dataset_type == 'freelook':
            saliency_dir = self.config.SALIENCY_FREELOOK_DIR
        elif dataset_type == 'scoring':
            saliency_dir = self.config.SALIENCY_SCORING_DIR
        else:
            raise ValueError(f"Unknown dataset type: {dataset_type}")
        
        filepath = saliency_dir / filename.replace('.jpg', '_COMBINED.jpg')
        
        if not filepath.exists():
            logger.warning(f"Saliency map not found: {filepath}")
            return None
        
        saliency = Image.open(filepath)
        saliency_array = np.array(saliency, dtype=np.float32)
        
        # Handle different channel formats
        if len(saliency_array.shape) == 3:
            # If RGB, convert to grayscale
            saliency_array = cv2.cvtColor(saliency_array.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        
        self.saliency_cache[cache_key] = saliency_array
        return saliency_array
    
    def normalize_saliency(self, saliency_map: np.ndarray, denoise: bool = False) -> np.ndarray:
        """
        Normalize saliency map to probability distribution.
        Args:
            saliency_map: Raw saliency map
            denoise: Apply Gaussian blur before normalization
        Returns:
            Normalized probability map
        """
        if saliency_map is None:
            return None
        
        # Clamp negative values
        saliency_clamped = np.maximum(saliency_map, 0)
        
        # Optional denoising
        if denoise and self.config.SALIENCY_DENOISE_SIGMA > 0:
            saliency_clamped = cv2.GaussianBlur(
                saliency_clamped, 
                (3, 3), 
                self.config.SALIENCY_DENOISE_SIGMA
            )
        
        # Normalize to probability
        total = np.sum(saliency_clamped) + self.config.EPSILON
        prob_map = saliency_clamped / total
        
        return prob_map
    
    def resize_saliency_to_image(self, saliency_map: np.ndarray, target_shape: Tuple) -> np.ndarray:
        """
        Resize saliency map to match image size.
        Args:
            saliency_map: Saliency map
            target_shape: (height, width) target size
        Returns:
            Resized saliency map
        """
        if saliency_map.shape[:2] == target_shape:
            return saliency_map
        
        resized = cv2.resize(saliency_map, (target_shape[1], target_shape[0]), 
                            interpolation=cv2.INTER_LINEAR)
        return resized
    
    def get_data_for_content(self, content_name: str, 
                            preprocess_saliency: bool = True) -> Dict:
        """
        Get all images and saliency maps for a given content.
        Returns:
            Dict with keys: 'images', 'saliency_freelook', 'saliency_scoring', 'levels'
        """
        levels = self.get_compression_levels(content_name)
        
        data = {
            'content_name': content_name,
            'levels': levels,
            'images': {},
            'saliency_freelook': {},
            'saliency_scoring': {},
        }
        
        for level in levels:
            # Find image file
            filename = f"{content_name}_jpgq_({level}).jpg"
            
            # Load image
            img = self.load_image(filename, color_space='ycrcb')
            data['images'][level] = img
            
            # Load saliency maps
            saliency_free = self.load_saliency_map(filename, dataset_type='freelook')
            saliency_score = self.load_saliency_map(filename, dataset_type='scoring')
            
            # Resize saliency maps to image size
            if saliency_free is not None:
                saliency_free = self.resize_saliency_to_image(saliency_free, img.shape[:2])
            if saliency_score is not None:
                saliency_score = self.resize_saliency_to_image(saliency_score, img.shape[:2])
            
            # Normalize to probability
            if preprocess_saliency:
                saliency_free = self.normalize_saliency(saliency_free, denoise=False)
                saliency_score = self.normalize_saliency(saliency_score, denoise=False)
            
            data['saliency_freelook'][level] = saliency_free
            data['saliency_scoring'][level] = saliency_score
        
        return data
    
    def clear_cache(self):
        """Clear image and saliency caches"""
        self.image_cache.clear()
        self.saliency_cache.clear()
        logger.info("Cache cleared")


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from config import config as default_config
    
    loader = DataLoader(default_config)
    contents = loader.get_unique_contents()
    print(f"Found {len(contents)} contents")
    print(f"First 5 contents: {contents[:5]}")
    
    # Test loading data for first content
    data = loader.get_data_for_content(contents[0])
    print(f"\nData for {contents[0]}:")
    print(f"  Levels: {data['levels']}")
    print(f"  Image shape: {data['images'][data['levels'][0]].shape}")
    print(f"  Saliency shape: {data['saliency_freelook'][data['levels'][0]].shape}")
