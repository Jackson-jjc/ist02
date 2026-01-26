#!/bin/bash

echo "════════════════════════════════════════════════════════════════"
echo "   伪影检测改进验证 - 快速检查工具"
echo "════════════════════════════════════════════════════════════════"

# 检查任务状态
echo ""
echo "📊 1. 任务状态"
echo "─────────────────────────────────────────────────────────────────"
squeue -j 533387 -o "%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R"

# 检查日志文件是否存在
if [ -f "logs/tas_main_533387.log" ]; then
    echo ""
    echo "📝 2. 最新日志（最后 20 行）"
    echo "─────────────────────────────────────────────────────────────────"
    tail -20 logs/tas_main_533387.log
else
    echo ""
    echo "📝 2. 日志文件"
    echo "─────────────────────────────────────────────────────────────────"
    ls -lh logs/tas_main* 2>/dev/null | tail -3
fi

# 检查结果文件
echo ""
echo "📋 3. 结果文件状态"
echo "─────────────────────────────────────────────────────────────────"
echo "RQ1 Task Shift: $([ -f 'results/rq1_task_shift_results.csv' ] && echo '✓ 存在' || echo '✗ 缺失')"
echo "RQ2 FR-TAS:     $([ -f 'results/rq2_prediction_fr_results.csv' ] && echo '✓ 存在' || echo '✗ 缺失')"
echo "RQ2 NR-TAS:     $([ -f 'results/rq2_prediction_nr_results.csv' ] && echo '✓ 存在' || echo '✗ 缺失')"
echo "RQ3 Consistency: $([ -f 'results/rq3_consistency_results.csv' ] && echo '✓ 存在' || echo '✗ 缺失')"
echo "RQ3 Distraction: $([ -f 'results/rq3_distraction_results.csv' ] && echo '✓ 存在' || echo '✗ 缺失')"

# 如果结果存在，显示关键指标
if [ -f 'results/rq2_prediction_nr_results.csv' ]; then
    echo ""
    echo "📈 4. 关键指标预览"
    echo "─────────────────────────────────────────────────────────────────"
    python3 << 'PYTHON_EOF'
import pandas as pd
import numpy as np

try:
    nr_df = pd.read_csv('results/rq2_prediction_nr_results.csv')
    fr_df = pd.read_csv('results/rq2_prediction_fr_results.csv')
    
    print(f"artifact_cc 平均值: {nr_df['artifact_cc'].mean():.4f}")
    print(f"artifact_cc 标准差: {nr_df['artifact_cc'].std():.4f}")
    print(f"artifact_cc 最大值: {nr_df['artifact_cc'].max():.4f}")
    print(f"artifact_cc 最小值: {nr_df['artifact_cc'].min():.4f}")
    
    print(f"\nNR-TAS CC 平均值: {nr_df['cc'].mean():.4f}")
    print(f"FR-TAS CC 平均值: {fr_df['cc'].mean():.4f}")
    
    # 判断改进是否成功
    if nr_df['artifact_cc'].mean() > 0.30:
        print("\n✅ 伪影检测改进成功! (artifact_cc > 0.30)")
    else:
        print(f"\n⚠️  伪影检测改进有限 (artifact_cc = {nr_df['artifact_cc'].mean():.4f})")
        
except FileNotFoundError:
    print("结果文件暂未生成，任务可能还在进行中...")
    
PYTHON_EOF
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "检查完毕"
echo "════════════════════════════════════════════════════════════════"
