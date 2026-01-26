#!/bin/bash
#SBATCH --job-name=TAS_Analysis_v4
#SBATCH --partition=swarm_a100
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:0
#SBATCH --mem=128G
#SBATCH --time=96:00:00
#SBATCH --output=TAS_v4-%j.out
#SBATCH --error=TAS_v4-%j.err
#SBATCH --mail-type=ALL,FAIL
#SBATCH --mail-user=jc15u24@soton.ac.uk

set -e

# ============================================================================
# TAS Experiments Pipeline - VERSION 4 (Improved with Fixes)
# 
# 实现方案 A 的全面修复:
#   1. 改进的伪影检测 (artifact_cc: 0.074 → 0.35+)
#   2. 优化的 TAS 模型 (停止 CC 恶化)
#   3. 3 个对照基线方法
#   4. 多数据集验证 (TUD + JIST01)
#
# 预计时间: 24-48 小时
# ============================================================================

# ============================================================================
# 环境配置
# ============================================================================

echo "[INFO] ============================================================================"
echo "[INFO] TAS EXPERIMENTS V4 - IMPROVED REPAIR VERSION"
echo "[INFO] ============================================================================"
echo "[INFO] Start Time: $(date)"

# 加载模块
source /etc/profile.d/modules.sh 2>/dev/null || true
module load conda 2>/dev/null || true

# 激活虚拟环境
CONDA_ENV="/iridisfs/home/jc15u24/.conda/envs/easygen-clean"
if [ -d "$CONDA_ENV" ]; then
    source activate "$CONDA_ENV"
    echo "[INFO] Activated conda environment: $CONDA_ENV"
else
    echo "[ERROR] Conda environment not found: $CONDA_ENV"
    exit 1
fi

# 设置环境变量
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK

# 项目配置
PROJECT_ROOT="/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments"
DATA_ROOT="/iridisfs/scratch/jc15u24/Code/IST02/TUD_Task_EyeTracking"
JIST01_DATA="/iridisfs/scratch/jc15u24/Code/JIST01/data"
RESULTS_DIR="$PROJECT_ROOT/results"
LOGS_DIR="$PROJECT_ROOT/logs"

# 验证目录
echo "[INFO] Verifying project structure..."
echo "[INFO] Project Root: $PROJECT_ROOT"
echo "[INFO] Data Root: $DATA_ROOT"
echo "[INFO] JIST01 Data: $JIST01_DATA"
echo "[INFO] Results Dir: $RESULTS_DIR"
echo "[INFO] Logs Dir: $LOGS_DIR"

if [ ! -d "$PROJECT_ROOT" ]; then
    echo "[ERROR] Project root not found: $PROJECT_ROOT"
    exit 1
fi

if [ ! -d "$DATA_ROOT" ]; then
    echo "[ERROR] Data root not found: $DATA_ROOT"
    exit 1
fi

# 创建输出目录
mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

# ============================================================================
# 系统信息
# ============================================================================

echo ""
echo "[INFO] ============================================================================"
echo "[INFO] SYSTEM INFORMATION"
echo "[INFO] ============================================================================"
echo "[INFO] Job ID: $SLURM_JOB_ID"
echo "[INFO] Job Name: $SLURM_JOB_NAME"
echo "[INFO] Node: $SLURM_NODELIST"
echo "[INFO] CPU Cores: $SLURM_CPUS_PER_TASK"
echo "[INFO] Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "[INFO] Python: $(python --version)"
echo "[INFO] NumPy: $(python -c 'import numpy; print(numpy.__version__)')"
echo "[INFO] OpenCV: $(python -c 'import cv2; print(cv2.__version__)')"

# ============================================================================
# 验证模块
# ============================================================================

echo ""
echo "[INFO] ============================================================================"
echo "[INFO] VALIDATING REQUIRED MODULES"
echo "[INFO] ============================================================================"

cd "$PROJECT_ROOT"

python << 'EOF'
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

required_modules = ['numpy', 'cv2', 'scipy', 'pandas', 'PIL']
missing = []

for module_name in required_modules:
    try:
        __import__(module_name)
        logger.info(f"✓ {module_name} available")
    except ImportError:
        logger.error(f"✗ {module_name} NOT available")
        missing.append(module_name)

if missing:
    logger.error(f"Missing modules: {missing}")
    sys.exit(1)

# Check if new modules exist
import os
from pathlib import Path

src_dir = Path('src')
required_files = [
    'artifact_maps_v2.py',
    'tas_model_v2.py',
    'baselines.py',
    'multi_dataset_loader.py'
]

for filename in required_files:
    filepath = src_dir / filename
    if filepath.exists():
        logger.info(f"✓ {filename} found")
    else:
        logger.error(f"✗ {filename} NOT found")
        sys.exit(1)

logger.info("\n[INFO] All validations passed!")
EOF

if [ $? -ne 0 ]; then
    echo "[ERROR] Module validation failed!"
    exit 1
fi

# ============================================================================
# 主实验运行
# ============================================================================

echo ""
echo "[INFO] ============================================================================"
echo "[INFO] RUNNING MAIN EXPERIMENTS V4"
echo "[INFO] ============================================================================"
echo "[INFO] Start Time: $(date)"

python improved_analysis_v4.py
RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo "[ERROR] Main experiments failed with code $RESULT"
    exit $RESULT
fi

echo "[INFO] Main experiments completed successfully!"
echo "[INFO] End Time: $(date)"

# ============================================================================
# 后续分析和报告生成
# ============================================================================

echo ""
echo "[INFO] ============================================================================"
echo "[INFO] GENERATING FINAL REPORT"
echo "[INFO] ============================================================================"

python << 'EOF'
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

results_dir = Path('results')
latest_files = sorted(results_dir.glob('results_*_v4_*.csv'), key=lambda x: x.stat().st_mtime, reverse=True)

if latest_files:
    print(f"[INFO] Latest results found: {latest_files[0].name}")
    
    # 读取最新结果
    df = pd.read_csv(latest_files[0])
    
    # 生成简要报告
    print("\n[INFO] ============================================================================")
    print("[INFO] EXPERIMENT SUMMARY")
    print("[INFO] ============================================================================")
    
    if 'cc_tas' in df.columns:
        print(f"FR-TAS CC: {df['cc_tas'].mean():.4f} ± {df['cc_tas'].std():.4f}")
        print(f"Artifact Detection Quality: {df['artifact_cc'].mean():.4f} ± {df['artifact_cc'].std():.4f}")
    
    if 'cc_tas_nr' in df.columns:
        print(f"NR-TAS CC: {df['cc_tas_nr'].mean():.4f} ± {df['cc_tas_nr'].std():.4f}")
    
    print(f"\nTotal samples processed: {len(df)}")
    print(f"Timestamp: {datetime.now()}")
else:
    print("[WARNING] No results found!")

EOF

# ============================================================================
# 清理和完成
# ============================================================================

echo ""
echo "[INFO] ============================================================================"
echo "[INFO] EXPERIMENTS COMPLETED"
echo "[INFO] ============================================================================"
echo "[INFO] End Time: $(date)"
echo "[INFO] Results saved to: $RESULTS_DIR"
echo "[INFO] Logs saved to: $LOGS_DIR"
echo "[INFO] Job completed successfully!"

exit 0
