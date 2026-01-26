#!/bin/bash
# Installation script for TAS experiments
# This script installs all required dependencies

echo "Installing TAS Experiments Dependencies..."
echo "=========================================="

# Install pip packages
pip install -q numpy scipy pandas opencv-python Pillow matplotlib scikit-image

echo ""
echo "✓ Installation complete!"
echo ""
echo "Ready to run experiments:"
echo "  python3 validate_setup.py     # Check setup"
echo "  python3 run_all_experiments.py # Run all experiments"
echo "  sbatch submit_experiments.slurm # Submit to SLURM"
