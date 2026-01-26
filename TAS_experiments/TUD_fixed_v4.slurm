#!/bin/bash
#SBATCH --job-name=TUD_Fixed_v4
#SBATCH --partition=swarm_a100
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --output=TUD_fixed_v4-%j.out
#SBATCH --error=TUD_fixed_v4-%j.err
#SBATCH --mail-type=ALL,FAIL
#SBATCH --mail-user=jc15u24@soton.ac.uk

set -e

# ============================================================================
# TUD 实验修复版本 v4
# 修复内容：
#   1. 正确加载 OriginalContent 中的 .bmp 原始图像
#   2. 改进原始图像加载逻辑，支持多种文件格式
#   3. 更好的错误处理和日志输出
# ============================================================================

# ============================================================================
# 环境配置
# ============================================================================

source /etc/profile.d/modules.sh || true
module load conda

CONDA_ENV="/iridisfs/home/jc15u24/.conda/envs/easygen-clean"
if [ -d "$CONDA_ENV" ]; then
    source activate "$CONDA_ENV"
    echo "[INFO] Activated conda environment: $CONDA_ENV"
else
    echo "[ERROR] Conda environment not found: $CONDA_ENV"
    exit 1
fi

# 让数值库用到申请的CPU核数
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export CUDA_VISIBLE_DEVICES=0

# 项目路径
PROJECT_ROOT="/iridisfs/scratch/jc15u24/Code/IST02"
TAS_EXPERIMENTS="$PROJECT_ROOT/TAS_experiments"
LOGS_DIR="$TAS_EXPERIMENTS/logs"
RESULTS_DIR="$TAS_EXPERIMENTS/results"

# 创建日志目录
mkdir -p "$LOGS_DIR"
mkdir -p "$RESULTS_DIR"

# 进入项目目录
cd "$TAS_EXPERIMENTS"

echo "================================================================================"
echo "TUD EXPERIMENTS - FIXED v4"
echo "================================================================================"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "CPU Cores: $SLURM_CPUS_PER_TASK"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo "Memory: ${SLURM_MEM_PER_NODE} MB"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Working Dir: $TAS_EXPERIMENTS"
echo "Logs Dir: $LOGS_DIR"
echo "Results Dir: $RESULTS_DIR"
echo "================================================================================"
echo ""

# ============================================================================
# PHASE 1: 数据验证和环境检查
# ============================================================================

echo "[PHASE 1] Validation and Setup"
echo "────────────────────────────────────────────────────────────────────────────"

# 验证数据集
if [ ! -d "$PROJECT_ROOT/TUD_Task_EyeTracking" ]; then
    echo "[ERROR] TUD dataset not found at $PROJECT_ROOT/TUD_Task_EyeTracking"
    exit 1
fi

echo "[✓] TUD dataset found"

# 验证依赖
python3 -c "import numpy, pandas, scipy, cv2, PIL; print('[✓] All dependencies imported successfully')" || {
    echo "[ERROR] Missing dependencies"
    exit 1
}

# 验证 Python 代码结构
if [ ! -f "$TAS_EXPERIMENTS/src/data_loader.py" ]; then
    echo "[ERROR] data_loader.py not found"
    exit 1
fi

if [ ! -f "$TAS_EXPERIMENTS/src/config.py" ]; then
    echo "[ERROR] config.py not found"
    exit 1
fi

echo "[✓] All validation checks passed"
echo ""

# ============================================================================
# PHASE 2: 运行修复后的主实验
# ============================================================================

echo "[PHASE 2] Running Fixed TAS Experiments"
echo "────────────────────────────────────────────────────────────────────────────"

python3 << 'PYTHON_SCRIPT'
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/tud_fixed_v4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from improved_analysis_v4 import ImprovedTASExperiment
    from config import config
    
    logger.info("="*80)
    logger.info("TAS EXPERIMENTS V4 - FIXED VERSION")
    logger.info("="*80)
    logger.info(f"Start Time: {datetime.now()}")
    logger.info(f"Project Root: {config.PROJECT_ROOT}")
    logger.info(f"Data Root: {config.DATA_ROOT}")
    logger.info(f"Results Dir: {config.RESULTS_DIR}")
    logger.info("")
    
    # 运行实验
    experiment = ImprovedTASExperiment()
    experiment.run_main_experiments_tud()
    
    logger.info("")
    logger.info("="*80)
    logger.info("EXPERIMENTS COMPLETED SUCCESSFULLY")
    logger.info("="*80)
    logger.info(f"End Time: {datetime.now()}")
    logger.info(f"Results saved to: {config.RESULTS_DIR}")
    logger.info(f"Logs saved to: {config.LOGS_DIR}")
    
except Exception as e:
    logger.error(f"Error running experiments: {e}", exc_info=True)
    sys.exit(1)

PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "[✓] Experiments completed successfully!"
else
    echo ""
    echo "[✗] Experiments failed!"
    exit 1
fi

echo ""
echo "================================================================================"
echo "Job completed successfully!"
echo "================================================================================"
