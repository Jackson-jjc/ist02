#!/usr/bin/env python3
"""
Quick validation script to check data and setup
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).parent / 'src'
sys.path.insert(0, str(SRC_DIR))

from config import config, DATA_ROOT, ORIGINAL_CONTENT_DIR, TEST_IMAGES_DIR, SALIENCY_FREELOOK_DIR, SALIENCY_SCORING_DIR
from data_loader import DataLoader

def validate_setup():
    """Validate that data and environment are properly set up"""
    
    print("=" * 80)
    print("TAS EXPERIMENTS - SETUP VALIDATION")
    print("=" * 80)
    
    # Check data paths
    print("\n1. Checking data paths...")
    paths_to_check = [
        ('Data root', DATA_ROOT),
        ('Original content', ORIGINAL_CONTENT_DIR),
        ('Test images', TEST_IMAGES_DIR),
        ('Saliency FreeLook', SALIENCY_FREELOOK_DIR),
        ('Saliency Scoring', SALIENCY_SCORING_DIR),
    ]
    
    all_good = True
    for name, path in paths_to_check:
        exists = path.exists()
        status = "✓" if exists else "✗"
        print(f"   {status} {name}: {path}")
        all_good = all_good and exists
    
    if not all_good:
        print("\n✗ Some data paths are missing!")
        return False
    
    # Load and check data
    print("\n2. Loading and checking data...")
    try:
        loader = DataLoader(config)
        contents = loader.get_unique_contents()
        print(f"   ✓ Found {len(contents)} unique contents")
        
        if len(contents) < 40:
            print(f"   ✗ Expected 40 contents, found {len(contents)}")
            return False
        
        # Test loading first content
        first_content = contents[0]
        print(f"\n3. Testing data loading ({first_content})...")
        data = loader.get_data_for_content(first_content, preprocess_saliency=True)
        
        print(f"   ✓ Levels: {data['levels']}")
        for level in data['levels']:
            img = data['images'][level]
            sal_free = data['saliency_freelook'][level]
            sal_score = data['saliency_scoring'][level]
            
            print(f"     Level {level}:")
            print(f"       Image shape: {img.shape}")
            print(f"       FreeLook shape: {sal_free.shape if sal_free is not None else 'None'}")
            print(f"       Scoring shape: {sal_score.shape if sal_score is not None else 'None'}")
        
        if not all(data['saliency_freelook'][l] is not None for l in data['levels']):
            print("   ✗ Some saliency maps are missing!")
            return False
        
        print("\n4. Checking output directories...")
        for name, path in [('Results', RESULTS_DIR), ('Logs', LOGS_DIR)]:
            path.mkdir(exist_ok=True)
            print(f"   ✓ {name}: {path}")
        
        print("\n" + "=" * 80)
        print("✓ ALL CHECKS PASSED - Ready to run experiments")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n✗ Error loading data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = validate_setup()
    sys.exit(0 if success else 1)
