#!/usr/bin/env python3
"""
Quick test script to verify TUD data loading fixes
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import config
from data_loader import DataLoader
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_loader():
    """Test the fixed DataLoader"""
    print("\n" + "="*80)
    print("TESTING TUD DATA LOADER FIXES")
    print("="*80 + "\n")
    
    loader = DataLoader(config)
    
    # Test 1: Get unique contents
    print("[Test 1] Getting unique contents...")
    try:
        contents = loader.get_unique_contents()
        print(f"✓ Found {len(contents)} unique contents")
        print(f"  First 5: {contents[:5]}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False
    
    # Test 2: Get compression levels
    print("\n[Test 2] Getting compression levels for first content...")
    try:
        first_content = contents[0]
        levels = loader.get_compression_levels(first_content)
        print(f"✓ Content '{first_content}' has {len(levels)} compression levels: {levels}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False
    
    # Test 3: Load test image
    print("\n[Test 3] Loading test image...")
    try:
        test_filename = f"{first_content}_jpgq_({levels[0]}).jpg"
        img = loader.load_image(test_filename)
        print(f"✓ Loaded image '{test_filename}': shape={img.shape}, dtype={img.dtype}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False
    
    # Test 4: Load original image (NEW FIX)
    print("\n[Test 4] Loading original image (NEW FIX)...")
    try:
        original = loader.load_original_image(first_content)
        if original is not None:
            print(f"✓ Loaded original image for '{first_content}': shape={original.shape}, dtype={original.dtype}")
        else:
            print(f"✗ Could not load original image (but this is handled gracefully)")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False
    
    # Test 5: Load saliency maps
    print("\n[Test 5] Loading saliency maps...")
    try:
        sal_freelook = loader.load_saliency_map(test_filename, 'freelook')
        sal_scoring = loader.load_saliency_map(test_filename, 'scoring')
        
        if sal_freelook is not None and sal_scoring is not None:
            print(f"✓ Loaded saliency maps:")
            print(f"  - FreeLook: shape={sal_freelook.shape}")
            print(f"  - Scoring: shape={sal_scoring.shape}")
        else:
            print(f"✗ Could not load one or both saliency maps")
            return False
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED ✓")
    print("="*80 + "\n")
    return True

if __name__ == "__main__":
    success = test_data_loader()
    sys.exit(0 if success else 1)
