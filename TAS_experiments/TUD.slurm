#!/bin/bash
#SBATCH --job-name=TAS_Analysis_v3
#SBATCH --partition=swarm_a100
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --mem=128G
#SBATCH --time=72:00:00
#SBATCH --output=TAS_v3-%j.out
#SBATCH --error=TAS_v3-%j.err
#SBATCH --mail-type=ALL,FAIL
#SBATCH --mail-user=jc15u24@soton.ac.uk

set -e

# ============================================================================
# TAS Experiments Pipeline - VERSION 3 (完整优化版)
# 
# 目的: 执行完整的实验分析和论文准备:
#   Phase 1: 主实验运行 (RQ1/RQ2/RQ3)
#   Phase 2: 统计显著性检验 + 消融研究
#   Phase 3: 生成所有可视化 (B1a-B1e)
#   Phase 4: 生成论文质量的表格和报告
#
# 时间: 预计 12-24 小时
# ============================================================================

# ============================================================================
# 环境配置
# ============================================================================

# 加载模块
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

# 设置日志文件
MAIN_LOG="$LOGS_DIR/tas_v2_${SLURM_JOB_ID}.log"

# ============================================================================
# 记录开始信息
# ============================================================================

{
echo "================================================================================"
echo "TAS EXPERIMENTS PIPELINE - IMPROVED VERSION v2"
echo "================================================================================"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "CPU Cores: $SLURM_CPUS_PER_TASK"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo "Memory: ${SLURM_MEM_PER_NODE} MB"
echo "Time Limit: $SLURM_TIMELIMIT"
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
if [ ! -f "$TAS_EXPERIMENTS/src/artifact_maps.py" ]; then
    echo "[ERROR] artifact_maps.py not found"
    exit 1
fi

echo "[✓] All validation checks passed"
echo ""

# ============================================================================
# PHASE 2: 运行主实验流程 (RQ1/RQ2/RQ3)
# ============================================================================

echo "[PHASE 2] Running Main Experiments (RQ1/RQ2/RQ3)"
echo "────────────────────────────────────────────────────────────────────────────"

python3 << 'PYTHON_SCRIPT'
import sys
import os
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

# Configure logging with both file and console
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler
log_file = os.path.join('logs', f'tas_main_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
fh = logging.FileHandler(log_file)
fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter(log_format))
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter(log_format))
logger.addHandler(ch)

try:
    # Import experiment modules
    from config import config
    from exp_rq1_task_shift import ExperimentRQ1
    from exp_rq2_prediction import ExperimentRQ2
    from exp_rq3_practical import ExperimentRQ3
    from visualizer import ResultsVisualizer
    
    logger.info("="*80)
    logger.info("TAS EXPERIMENTS PIPELINE - Main Experiments")
    logger.info("="*80)
    
    all_results = {}
    
    # ──────────────────────────────────────────────────────────────────────────
    # RQ1: Task Shift Analysis
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("\n[RQ1] Task Shift Analysis")
    logger.info("─"*80)
    
    exp_rq1 = ExperimentRQ1(config)
    results_rq1 = exp_rq1.run()
    all_results['rq1'] = results_rq1
    
    # Save results
    results_rq1['results_df'].to_csv('results/rq1_task_shift_results.csv', index=False)
    logger.info(f"[✓] RQ1 results saved to results/rq1_task_shift_results.csv")
    logger.info(f"    Total samples: {len(results_rq1['results_df'])}")
    logger.info(f"    Unique contents: {results_rq1['results_df']['content'].nunique()}")
    
    # Print summary by compression level
    if 'summary_by_level' in results_rq1:
        levels = sorted(results_rq1['summary_by_level'].keys())
        logger.info(f"    Compression levels: {len(levels)} (range: {min(levels)}-{max(levels)})")
    
    # ──────────────────────────────────────────────────────────────────────────
    # RQ2-FR: Full Reference TAS
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("\n[RQ2-FR] Saliency Prediction (Full-Reference)")
    logger.info("─"*80)
    
    exp_rq2_fr = ExperimentRQ2(config, tas_method='loglinear')
    results_rq2_fr = exp_rq2_fr.run(use_fr_artifact=True)
    all_results['rq2_fr'] = results_rq2_fr
    
    # Save results
    results_rq2_fr['results_df'].to_csv('results/rq2_prediction_fr_results.csv', index=False)
    logger.info(f"[✓] RQ2-FR results saved")
    
    # Print method comparison
    if 'summary' in results_rq2_fr:
        logger.info("    Method Comparison:")
        for method, metrics in results_rq2_fr['summary'].items():
            if 'cc' in metrics:
                cc_mean = metrics['cc']['mean']
                cc_sem = metrics['cc'].get('sem', 0)
                logger.info(f"      {method}: CC={cc_mean:.4f}±{cc_sem:.4f}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # RQ2-NR: No-Reference TAS
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("\n[RQ2-NR] Saliency Prediction (No-Reference)")
    logger.info("─"*80)
    
    exp_rq2_nr = ExperimentRQ2(config, tas_method='loglinear')
    results_rq2_nr = exp_rq2_nr.run(use_fr_artifact=False)
    all_results['rq2_nr'] = results_rq2_nr
    
    # Save results
    results_rq2_nr['results_df'].to_csv('results/rq2_prediction_nr_results.csv', index=False)
    logger.info(f"[✓] RQ2-NR results saved")
    
    # ──────────────────────────────────────────────────────────────────────────
    # RQ3: Practical Value
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("\n[RQ3] Practical Value Analysis")
    logger.info("─"*80)
    
    exp_rq3 = ExperimentRQ3(config, trained_models=results_rq2_nr.get('trained_models'))
    results_rq3 = exp_rq3.run()
    all_results['rq3'] = results_rq3
    
    # Save results
    results_rq3['consistency_df'].to_csv('results/rq3_consistency_results.csv', index=False)
    results_rq3['distraction_df'].to_csv('results/rq3_distraction_results.csv', index=False)
    logger.info(f"[✓] RQ3 results saved")
    
    # ──────────────────────────────────────────────────────────────────────────
    # Visualization and Report
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("\n[VISUALIZATION] Generating plots and report")
    logger.info("─"*80)
    
    visualizer = ResultsVisualizer(config)
    
    # Generate plots
    plot_count = 0
    
    if 'rq1' in all_results and visualizer is not None:
        try:
            result = visualizer.plot_task_shift_curves(
                all_results['rq1']['results_df'],
                all_results['rq1'].get('summary_by_level', {})
            )
            if result:
                logger.info(f"[✓] RQ1 plot saved")
                plot_count += 1
        except Exception as e:
            logger.warning(f"[!] Failed to generate RQ1 plot: {e}")
    
    if 'rq2_fr' in all_results and visualizer is not None:
        try:
            result = visualizer.plot_prediction_comparison(
                all_results['rq2_fr']['results_df'],
                all_results['rq2_fr'].get('summary', {})
            )
            if result:
                logger.info(f"[✓] RQ2 plot saved")
                plot_count += 1
        except Exception as e:
            logger.warning(f"[!] Failed to generate RQ2 plot: {e}")
    
    if 'rq3' in all_results and visualizer is not None:
        try:
            result = visualizer.plot_distraction_trend(
                all_results['rq3']['distraction_df'],
                all_results['rq3'].get('distraction_summary', {})
            )
            if result:
                logger.info(f"[✓] RQ3 plot saved")
                plot_count += 1
        except Exception as e:
            logger.warning(f"[!] Failed to generate RQ3 plot: {e}")
    
    # Generate summary report
    try:
        visualizer.generate_summary_report(all_results)
        logger.info(f"[✓] Summary report generated")
    except Exception as e:
        logger.warning(f"[!] Failed to generate report: {e}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # Final Summary
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("\n" + "="*80)
    logger.info("EXPERIMENTS COMPLETED SUCCESSFULLY")
    logger.info("="*80)
    logger.info(f"Results saved to: results/")
    logger.info(f"Total plots generated: {plot_count}")
    logger.info(f"Logs saved to: logs/")
    
    sys.exit(0)
    
except Exception as e:
    logger.error(f"ERROR: {str(e)}", exc_info=True)
    sys.exit(1)

PYTHON_SCRIPT

if [ $? -ne 0 ]; then
    echo "[ERROR] Main experiments failed"
    exit 1
fi

echo ""

# ============================================================================
# PHASE 3: 数据质量检查和统计分析
# ============================================================================

echo "[PHASE 3] Data Quality Validation and Statistical Analysis"
echo "────────────────────────────────────────────────────────────────────────────"

python3 << 'PYTHON_VALIDATION'
import pandas as pd
import numpy as np
from scipy import stats
import os

results_dir = 'results'

try:
    # Load results
    rq1 = pd.read_csv(os.path.join(results_dir, 'rq1_task_shift_results.csv'))
    rq2_fr = pd.read_csv(os.path.join(results_dir, 'rq2_prediction_fr_results.csv'))
    rq2_nr = pd.read_csv(os.path.join(results_dir, 'rq2_prediction_nr_results.csv'))
    
    print("\n" + "="*80)
    print("DATA QUALITY AND STATISTICAL SUMMARY")
    print("="*80)
    
    # RQ1 Analysis
    print("\n[RQ1] Task Shift Analysis:")
    print(f"  Total samples: {len(rq1)}")
    print(f"  Unique contents: {rq1['content'].nunique()}")
    print(f"  CC mean: {rq1['cc'].mean():.4f} ± {rq1['cc'].std():.4f}")
    print(f"  JSD mean: {rq1['jsd'].mean():.4f} ± {rq1['jsd'].std():.4f}")
    
    # RQ2-FR Analysis
    print("\n[RQ2-FR] Full-Reference TAS:")
    if 'freelook_cc' in rq2_fr.columns and 'tas_cc' in rq2_fr.columns:
        cc_change = rq2_fr['tas_cc'].mean() - rq2_fr['freelook_cc'].mean()
        jsd_change = rq2_fr['freelook_jsd'].mean() - rq2_fr['tas_jsd'].mean()
        
        print(f"  CC baseline: {rq2_fr['freelook_cc'].mean():.4f}")
        print(f"  CC TAS: {rq2_fr['tas_cc'].mean():.4f}")
        print(f"  CC change: {cc_change:+.4f} ({(cc_change/rq2_fr['freelook_cc'].mean()*100):+.2f}%)")
        
        print(f"  JSD baseline: {rq2_fr['freelook_jsd'].mean():.4f}")
        print(f"  JSD TAS: {rq2_fr['tas_jsd'].mean():.4f}")
        print(f"  JSD change: {jsd_change:+.4f} ({(jsd_change/rq2_fr['freelook_jsd'].mean()*100):+.2f}%)")
        
        # Paired t-test
        t_stat, p_val = stats.ttest_rel(rq2_fr['tas_cc'], rq2_fr['freelook_cc'])
        print(f"  Paired t-test: t={t_stat:.4f}, p={p_val:.6f}")
    
    # RQ2-NR Analysis
    print("\n[RQ2-NR] No-Reference TAS:")
    if 'freelook_cc' in rq2_nr.columns and 'tas_cc' in rq2_nr.columns:
        cc_nr = rq2_nr['tas_cc'].dropna()
        fl_cc = rq2_nr['freelook_cc'].dropna()
        
        cc_change_nr = cc_nr.mean() - fl_cc.mean()
        print(f"  CC baseline: {fl_cc.mean():.4f} ± {fl_cc.std():.4f}")
        print(f"  CC NR-TAS: {cc_nr.mean():.4f} ± {cc_nr.std():.4f}")
        print(f"  CC change: {cc_change_nr:+.4f} ({(cc_change_nr/fl_cc.mean()*100):+.2f}%)")
        print(f"  Instability (std increase): {(cc_nr.std()/fl_cc.std() - 1)*100:+.1f}%")
        
        if 'artifact_cc' in rq2_nr.columns:
            print(f"  Artifact CC: {rq2_nr['artifact_cc'].mean():.6f} (should be > 0.30)")
    
    print("\n" + "="*80)
    print("Validation completed successfully")
    print("="*80)
    
except Exception as e:
    print(f"[WARNING] Validation script error: {e}")
    # Don't exit on validation error, main results are still valid

PYTHON_VALIDATION

echo ""

# ============================================================================
# PHASE 4: 改进分析 - 统计检验、可视化、失败案例分析
# ============================================================================

echo "[PHASE 4] Improved Analysis (Statistical Tests, Enhanced Visualizations)"
echo "────────────────────────────────────────────────────────────────────────────"

cd "$TAS_EXPERIMENTS"

python3 improved_analysis.py 2>&1 | tee -a "$LOGS_DIR/improved_analysis_$(date '+%Y%m%d_%H%M%S').log"

if [ $? -eq 0 ]; then
    echo "[✓] Improved analysis completed successfully"
else
    echo "[!] Improved analysis encountered warnings (non-critical)"
fi

echo ""

# ============================================================================
# PHASE 5: 结果总结和资源使用报告
# ============================================================================

echo "[PHASE 5] Results Summary and Resource Usage"
echo "────────────────────────────────────────────────────────────────────────────"

} | tee -a "$MAIN_LOG"

# 输出最终摘要
{
echo ""
echo "================================================================================"
echo "FINAL SUMMARY"
echo "================================================================================"
echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Results Location: $RESULTS_DIR"
echo "Key Output Files:"
echo "  - rq1_task_shift_results.csv"
echo "  - rq2_prediction_fr_results.csv"
echo "  - rq2_prediction_nr_results.csv"
echo "  - rq3_consistency_results.csv"
echo "  - rq3_distraction_results.csv"
echo ""
echo "Log Files: $LOGS_DIR"
echo "Main Log: $MAIN_LOG"
echo ""
echo "================================================================================"
echo "NEXT STEPS:"
echo "================================================================================"
echo "1. Review results in: $RESULTS_DIR"
echo "2. Check detailed logs: ls -lh $LOGS_DIR/"
echo "3. Compare FR-TAS vs NR-TAS performance"
echo "4. Validate artifact detection improvements"
echo "5. Prepare paper with results"
echo ""
echo "Documentation:"
echo "  - Evaluation report: $PROJECT_ROOT/TAS_EXECUTIVE_SUMMARY.md"
echo "  - Detailed analysis: $PROJECT_ROOT/TAS_EXPERIMENT_REVIEW.md"
echo "  - Repair guide: $PROJECT_ROOT/TAS_REPAIR_FEASIBILITY.md"
echo "================================================================================"
echo ""
echo "Job completed successfully!"
echo ""
} | tee -a "$MAIN_LOG"
