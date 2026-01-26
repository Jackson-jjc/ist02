#!/bin/bash
#SBATCH --job-name=TAS_Tasks_7-9
#SBATCH --partition=swarm_a100
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:0
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=TAS_tasks_7-9-%j.out
#SBATCH --error=TAS_tasks_7-9-%j.err
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=jc15u24@soton.ac.uk

set -e

# ============================================================================
# TAS 补充任务 7-9: 可视化 + 亚组分析 + 失败案例
# 
# 任务7: 轨迹可视化 - 生成最佳/典型/最差案例的对比图
# 任务8: 亚组分析 - 按内容复杂度分层统计和假设检验
# 任务9: 失败案例 - 深度分析最差内容的共同特征
#
# 预计时间: 3-5小时
# ============================================================================

# 加载环境
source /etc/profile.d/modules.sh || true
module load conda

# 激活虚拟环境
CONDA_ENV="/iridisfs/home/jc15u24/.conda/envs/easygen-clean"
if [ -d "$CONDA_ENV" ]; then
    source activate "$CONDA_ENV"
    echo "[INFO] Activated conda environment: $CONDA_ENV"
else
    echo "[ERROR] Conda environment not found: $CONDA_ENV"
    exit 1
fi

# 设置路径
PROJECT_ROOT="/iridisfs/scratch/jc15u24/Code/IST02"
TAS_DIR="$PROJECT_ROOT/TAS_experiments"
RESULTS_DIR="$TAS_DIR/results"
LOGS_DIR="$TAS_DIR/logs"

mkdir -p "$LOGS_DIR" "$RESULTS_DIR"
cd "$TAS_DIR"

# 日志文件
LOG_FILE="$LOGS_DIR/tasks_7-9_${SLURM_JOB_ID}.log"

# ============================================================================
# 记录开始信息
# ============================================================================

{
echo "================================================================================"
echo "TAS TASKS 7-9: VISUALIZATION, SUBGROUP ANALYSIS, FAILURE CASE ANALYSIS"
echo "================================================================================"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "CPU Cores: $SLURM_CPUS_PER_TASK"
echo "Memory: ${SLURM_MEM_PER_NODE} MB"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Working Dir: $TAS_DIR"
echo "Logs Dir: $LOGS_DIR"
echo "Results Dir: $RESULTS_DIR"
echo "================================================================================"
echo ""

# ============================================================================
# PHASE 1: 验证数据
# ============================================================================

echo "[PHASE 1] 验证数据和环境"
echo "────────────────────────────────────────────────────────────────────────────"

# 检查结果文件
RESULT_FILE=$(ls -t "$RESULTS_DIR"/results_nr_v4_*.csv 2>/dev/null | head -1)
if [ ! -f "$RESULT_FILE" ]; then
    echo "[ERROR] 未找到结果文件!"
    exit 1
fi

echo "[✓] 找到结果文件: $(basename $RESULT_FILE)"
SAMPLE_COUNT=$(wc -l < "$RESULT_FILE")
echo "[✓] 样本数: $SAMPLE_COUNT"

# 检查Python模块
echo ""
echo "[检查Python依赖...]"
python3 << 'PYTHON_CHECK'
try:
    import matplotlib
    import pandas
    import numpy
    import scipy
    print("[✓] 所有依赖已安装")
except ImportError as e:
    print(f"[ERROR] 缺少依赖: {e}")
    exit(1)
PYTHON_CHECK

# ============================================================================
# PHASE 2: 任务7 - 轨迹可视化
# ============================================================================

echo ""
echo "[PHASE 2] 任务7 - 轨迹可视化示例"
echo "────────────────────────────────────────────────────────────────────────────"
echo "目标: 生成最佳/典型/最差内容的对比图"
echo ""

cd "$TAS_DIR"
python3 << 'TASK7'
import sys
sys.path.insert(0, '/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments')

import logging
logging.basicConfig(level=logging.INFO, 
                   format='[%(levelname)s] %(message)s')

try:
    from src.task7_trajectory_visualization import TrajectoryVisualizer
    from src.config import Config
    import glob
    
    config = Config()
    
    # 找最新结果文件
    result_files = sorted(glob.glob(str(config.RESULTS_DIR / 'results_nr_v4_*.csv')))
    if not result_files:
        print("[ERROR] 未找到结果文件")
        exit(1)
    
    latest_file = result_files[-1]
    print(f"[INFO] 使用结果文件: {latest_file}")
    
    # 生成可视化
    visualizer = TrajectoryVisualizer(str(config.RESULTS_DIR), latest_file)
    result = visualizer.generate_all_figures()
    
    print(f"\n[SUCCESS] 任务7完成!")
    print(f"  生成的图表: {len(result['figures'])} 个")
    print(f"  保存位置: {visualizer.output_dir}")
    
except Exception as e:
    print(f"[ERROR] 任务7失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
TASK7

if [ $? -ne 0 ]; then
    echo "[ERROR] 任务7执行失败!"
    exit 1
fi

# ============================================================================
# PHASE 3: 任务8 - 亚组分析
# ============================================================================

echo ""
echo "[PHASE 3] 任务8 - 亚组分析"
echo "────────────────────────────────────────────────────────────────────────────"
echo "目标: 按内容复杂度分层，执行Kruskal-Wallis检验"
echo ""

python3 << 'TASK8'
import sys
sys.path.insert(0, '/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments')

import logging
logging.basicConfig(level=logging.INFO,
                   format='[%(levelname)s] %(message)s')

try:
    from src.task8_subgroup_analysis import SubgroupAnalyzer
    from src.config import Config
    import glob
    
    config = Config()
    
    # 找最新结果文件
    result_files = sorted(glob.glob(str(config.RESULTS_DIR / 'results_nr_v4_*.csv')))
    latest_file = result_files[-1]
    
    print(f"[INFO] 使用结果文件: {latest_file}")
    
    # 执行亚组分析
    analyzer = SubgroupAnalyzer(latest_file, str(config.RESULTS_DIR))
    report = analyzer.generate_comprehensive_report()
    
    print(f"\n[SUCCESS] 任务8完成!")
    print(f"  H-statistic: {report['kruskal_wallis_test']['h_statistic']:.4f}")
    print(f"  p-value: {report['kruskal_wallis_test']['p_value']:.4e}")
    
except Exception as e:
    print(f"[ERROR] 任务8失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
TASK8

if [ $? -ne 0 ]; then
    echo "[ERROR] 任务8执行失败!"
    exit 1
fi

# ============================================================================
# PHASE 4: 任务9 - 失败案例分析
# ============================================================================

echo ""
echo "[PHASE 4] 任务9 - 失败案例分析"
echo "────────────────────────────────────────────────────────────────────────────"
echo "目标: 深度分析最差内容的共同特征和改进建议"
echo ""

python3 << 'TASK9'
import sys
sys.path.insert(0, '/iridisfs/scratch/jc15u24/Code/IST02/TAS_experiments')

import logging
logging.basicConfig(level=logging.INFO,
                   format='[%(levelname)s] %(message)s')

try:
    from src.task9_failure_case_analysis import FailureCaseAnalyzer
    from src.config import Config
    import glob
    
    config = Config()
    
    # 找最新结果文件
    result_files = sorted(glob.glob(str(config.RESULTS_DIR / 'results_nr_v4_*.csv')))
    latest_file = result_files[-1]
    
    print(f"[INFO] 使用结果文件: {latest_file}")
    
    # 执行失败案例分析
    analyzer = FailureCaseAnalyzer(latest_file, str(config.RESULTS_DIR))
    report = analyzer.generate_failure_report()
    
    print(f"\n[SUCCESS] 任务9完成!")
    print(f"  分析了 {len(report['worst_cases'])} 个最差案例")
    print(f"  生成了 {len(report['improvement_suggestions'])} 条改进建议")
    
except Exception as e:
    print(f"[ERROR] 任务9失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
TASK9

if [ $? -ne 0 ]; then
    echo "[ERROR] 任务9执行失败!"
    exit 1
fi

# ============================================================================
# 总结
# ============================================================================

echo ""
echo "================================================================================"
echo "✓ 所有任务完成!"
echo "================================================================================"
echo ""
echo "生成的文件:"
ls -lh "$RESULTS_DIR"/fig_*.pdf 2>/dev/null || echo "  (图表文件)"
ls -lh "$RESULTS_DIR"/table_*.csv 2>/dev/null || echo "  (统计表格)"
ls -lh "$RESULTS_DIR"/*analysis*.json 2>/dev/null || echo "  (分析报告)"
echo ""
echo "下一步:"
echo "  1. 检查图表质量: $RESULTS_DIR/fig_*.pdf"
echo "  2. 查看统计结果: $RESULTS_DIR/table_*.csv"
echo "  3. 查看详细分析: $RESULTS_DIR/*analysis*.json"
echo ""
echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"

} | tee "$LOG_FILE"

echo ""
echo "[✓] 日志已保存: $LOG_FILE"
echo "[✓] 任务7-9已完成，数据已准备好投稿!"
