#!/bin/bash
#SBATCH --job-name=TAS_Improvement_v2
#SBATCH --partition=swarm_a100
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:0
#SBATCH --mem=32G
#SBATCH --time=2:00:00
#SBATCH --output=TAS_Improvement_v2-%j.out
#SBATCH --error=TAS_Improvement_v2-%j.err
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=jc15u24@soton.ac.uk

set -e

# ============================================================================
# TAS实验改进工作 - 版本2 (修复版)
#
# 任务:
#   1. JIST01多数据集加载和分析
#   2. 完整统计检验补充
#   3. 生成论文所需的所有表格
#
# 耗时: 预计 30-60 分钟
# ============================================================================

# 加载环境
source /etc/profile.d/modules.sh || true
module load conda

# 激活虚拟环境
CONDA_ENV="/iridisfs/home/jc15u24/.conda/envs/easygen-clean"
source activate "$CONDA_ENV"

# 设置环境变量
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4

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

# 记录开始
echo "================================================================================"
echo "TAS实验改进工作 - 版本2 (修复版)"
echo "================================================================================"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "任务ID: $SLURM_JOB_ID"
echo "CPU核心: $SLURM_CPUS_PER_TASK"
echo "内存: $SLURM_MEM_PER_NODE MB"
echo "项目: $TAS_EXPERIMENTS"
echo "================================================================================"
echo ""

# ============================================================================
# Phase 1: 环境验证
# ============================================================================

echo "[PHASE 1] 环境验证和数据检查"
echo "────────────────────────────────────────────────────────────────────────────"

# 检查TUD数据
if [ ! -d "$PROJECT_ROOT/TUD_Task_EyeTracking" ]; then
    echo "[✗] TUD数据集未找到"
    exit 1
fi
echo "[✓] TUD数据集验证通过"

# 检查JIST01数据
if [ ! -d "$PROJECT_ROOT/../JIST01/data/fixation/fixation" ]; then
    echo "[✗] JIST01数据集未找到"
    exit 1
fi
echo "[✓] JIST01数据集验证通过"

# 检查Python依赖
python3 << 'PYTHON_CHECK'
import sys
try:
    import numpy
    import pandas
    import scipy
    import scipy.io
    print("[✓] 所有Python依赖验证通过")
except ImportError as e:
    print(f"[✗] 缺少依赖: {e}")
    sys.exit(1)
PYTHON_CHECK

echo ""

# ============================================================================
# Phase 2: 运行改进任务
# ============================================================================

echo "[PHASE 2] 执行改进任务"
echo "────────────────────────────────────────────────────────────────────────────"

python3 << 'PYTHON_SCRIPT'
import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, 'src')

# 配置日志
log_file = f"logs/improvement_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("="*80)
logger.info("开始执行改进任务")
logger.info("="*80)

# ============================================================================
# Task 1: JIST01数据加载
# ============================================================================

logger.info("")
logger.info("[Task 1] 加载JIST01数据集")
logger.info("-" * 80)

try:
    from src.jist01_loader import JIST01Loader
    
    loader = JIST01Loader('/iridisfs/scratch/jc15u24/Code/JIST01/data')
    
    # 加载关键变换
    transformations = ['Reference', 'MotionBlur_1', 'Compression_1']
    jist01_data = loader.load_all_transformations(transformations)
    
    if len(jist01_data) > 0:
        logger.info(f"✓ 成功加载 {len(jist01_data)} 种变换")
        total_images = sum(d['n_images'] for d in jist01_data.values())
        logger.info(f"✓ 总共 {total_images} 张显著性图")
    else:
        logger.error("✗ 无法加载JIST01数据")
        sys.exit(1)
        
except Exception as e:
    logger.error(f"✗ JIST01加载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Task 2: 统计分析
# ============================================================================

logger.info("")
logger.info("[Task 2] 执行完整统计分析")
logger.info("-" * 80)

try:
    from src.statistical_analyzer import generate_complete_statistical_report
    
    report = generate_complete_statistical_report('results')
    
    if report:
        logger.info("✓ 统计分析完成")
        logger.info(f"  - 生成文件: table_method_comparison.csv")
        logger.info(f"  - 生成文件: table_statistical_tests.csv")
    else:
        logger.warning("⚠ 统计分析返回空结果")
        
except Exception as e:
    logger.error(f"✗ 统计分析失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# Task 3: 跨数据集对比
# ============================================================================

logger.info("")
logger.info("[Task 3] 生成跨数据集对比")
logger.info("-" * 80)

try:
    from src.cross_dataset_analyzer import CrossDatasetAnalyzer
    
    analyzer = CrossDatasetAnalyzer('results')
    
    # 再次加载JIST01用于对比
    trans_comparison = analyzer.compare_transformations(jist01_data)
    trans_comparison.to_csv('results/jist01_transformation_comparison.csv', index=False)
    
    logger.info(f"✓ 跨数据集对比完成")
    logger.info(f"  - 对比了 {len(trans_comparison)} 种变换")
    
except Exception as e:
    logger.error(f"✗ 跨数据集对比失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 完成总结
# ============================================================================

logger.info("")
logger.info("="*80)
logger.info("✓ 改进工作完成!")
logger.info("="*80)
logger.info("")
logger.info("生成的文件:")
logger.info("  - results/table_method_comparison.csv")
logger.info("  - results/table_statistical_tests.csv")
logger.info("  - results/jist01_transformation_comparison.csv")
logger.info("")
logger.info("下一步:")
logger.info("  1. 查看results/目录中的表格文件")
logger.info("  2. 将表格复制到论文中")
logger.info("  3. 完成Methods和Results部分")
logger.info("")

PYTHON_SCRIPT

PYTHON_EXIT_CODE=$?

echo ""
echo "="*80

if [ $PYTHON_EXIT_CODE -eq 0 ]; then
    echo "✓ 任务完成成功!"
    echo "="*80
    
    # 列出生成的文件
    echo ""
    echo "生成的核心文件:"
    ls -lh results/table_*.csv results/*transformation*.csv 2>/dev/null || true
    
    echo ""
    echo "结果已保存到: results/ 目录"
    exit 0
else
    echo "✗ 任务执行失败 (exit code: $PYTHON_EXIT_CODE)"
    echo "="*80
    echo ""
    echo "请检查错误日志: logs/ 目录"
    exit 1
fi
