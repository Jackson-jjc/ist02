"""
Advanced Analysis Module
- Statistical significance testing
- Ablation studies
- Failure case analysis
- Enhanced visualization
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, List
import logging
from scipy import stats
from scipy.stats import ttest_rel, mannwhitneyu, f_oneway
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class StatisticalAnalysis:
    """Comprehensive statistical significance testing"""
    
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha
        self.results = {}
    
    def paired_t_test(self, x, y, method1: str, method2: str) -> Dict:
        """Perform paired t-test between two methods"""
        t_stat, p_value = ttest_rel(x, y)
        cohens_d = (x.mean() - y.mean()) / np.sqrt((x.std()**2 + y.std()**2) / 2)
        
        sig = "***" if p_value < 0.001 else ("**" if p_value < 0.01 else ("*" if p_value < 0.05 else "ns"))
        improvement = ((x.mean() - y.mean()) / y.mean()) * 100
        
        result = {
            'method1': method1,
            'method2': method2,
            'mean_diff': x.mean() - y.mean(),
            'std_x': x.std(),
            'std_y': y.std(),
            'ci_lower': x.mean() - y.mean() - 1.96 * np.sqrt((x.std()**2 + y.std()**2) / len(x)),
            'ci_upper': x.mean() - y.mean() + 1.96 * np.sqrt((x.std()**2 + y.std()**2) / len(x)),
            't_stat': t_stat,
            'p_value': p_value,
            'cohens_d': cohens_d,
            'significance': sig,
            'improvement_pct': improvement
        }
        return result
    
    def bonferroni_correction(self, p_values: List[float], n_tests: int = None) -> List[str]:
        """Apply Bonferroni correction to p-values"""
        if n_tests is None:
            n_tests = len(p_values)
        corrected = [min(p * n_tests, 1.0) for p in p_values]
        return ["***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns")) 
                for p in corrected]
    
    def effect_size_interpretation(self, cohens_d: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"
    
    def generate_comparison_table(self, rq2_data: pd.DataFrame) -> pd.DataFrame:
        """Generate formatted comparison table with statistics"""
        methods = ['freelook_cc', 'artifact_cc', 'mixture_cc', 'tas_cc']
        method_names = ['FreeLook', 'Artifact', 'Mixture', 'TAS']
        
        comparison_data = []
        
        for i, (method, name) in enumerate(zip(methods, method_names)):
            data = rq2_data[method].dropna()
            
            # Calculate statistics
            mean = data.mean()
            std = data.std()
            sem = data.sem()  # Standard error of mean
            ci_lower = mean - 1.96 * sem
            ci_upper = mean + 1.96 * sem
            median = data.median()
            min_val = data.min()
            max_val = data.max()
            
            comparison_data.append({
                'Method': name,
                'Mean': f"{mean:.4f}",
                '±SD': f"{std:.4f}",
                '[95% CI]': f"[{ci_lower:.4f}, {ci_upper:.4f}]",
                'Median': f"{median:.4f}",
                'Min': f"{min_val:.4f}",
                'Max': f"{max_val:.4f}",
                'N': len(data)
            })
        
        return pd.DataFrame(comparison_data)
    
    def pairwise_comparisons_vs_baseline(self, rq2_data: pd.DataFrame, baseline: str = 'freelook_cc') -> Dict:
        """Perform pairwise t-tests vs baseline method"""
        baseline_data = rq2_data[baseline].dropna()
        
        other_methods = [m for m in ['artifact_cc', 'mixture_cc', 'tas_cc'] 
                        if m in rq2_data.columns and m != baseline]
        method_names = {'artifact_cc': 'Artifact', 'mixture_cc': 'Mixture', 'tas_cc': 'TAS'}
        
        comparisons = []
        for method in other_methods:
            method_data = rq2_data[method].dropna()
            
            # Ensure same length
            min_len = min(len(baseline_data), len(method_data))
            baseline_data_aligned = baseline_data.iloc[:min_len].values
            method_data_aligned = method_data.iloc[:min_len].values
            
            result = self.paired_t_test(method_data_aligned, baseline_data_aligned, 
                                       method_names[method], 'FreeLook')
            comparisons.append(result)
        
        return comparisons


class AblationStudy:
    """Perform ablation studies on model components"""
    
    def __init__(self, config):
        self.config = config
    
    def test_fusion_methods(self, freelook_pred: np.ndarray, 
                           artifact_score: np.ndarray,
                           content_prior: np.ndarray,
                           target: np.ndarray) -> Dict:
        """
        Compare different fusion strategies:
        1. Linear: α*P_f + β*A + γ*P_C
        2. Log-linear: P_f^α * A^β * P_C^γ
        3. Exponential: exp(α*log(P_f) + β*log(A) + γ*log(P_C))
        """
        from scipy.optimize import minimize
        
        def linear_fusion(params, P_f, A, P_C, target):
            alpha, beta, gamma = params
            pred = alpha * P_f + beta * A + gamma * P_C
            # Clip to [0, 1]
            pred = np.clip(pred, 0, 1)
            cc = np.corrcoef(pred, target)[0, 1]
            return -cc  # Negative because we minimize
        
        def log_linear_fusion(params, P_f, A, P_C, target):
            alpha, beta, gamma = params
            # Avoid log(0)
            P_f = np.clip(P_f, 1e-10, 1)
            A = np.clip(A, 1e-10, 1)
            P_C = np.clip(P_C, 1e-10, 1)
            
            pred = (P_f ** alpha) * (A ** beta) * (P_C ** gamma)
            pred = np.clip(pred, 0, 1)
            
            if np.any(np.isnan(pred)) or np.any(np.isinf(pred)):
                return 1e10
            
            cc = np.corrcoef(pred, target)[0, 1]
            return -cc if not np.isnan(cc) else 1e10
        
        results = {}
        
        # Test Linear
        try:
            res_linear = minimize(linear_fusion, [0.5, 0.1, 0.5],
                                 args=(freelook_pred, artifact_score, content_prior, target),
                                 bounds=[(0, 1), (0, 0.5), (0, 1)])
            results['linear'] = {
                'params': res_linear.x,
                'performance': -res_linear.fun
            }
        except Exception as e:
            logger.warning(f"Linear fusion failed: {e}")
            results['linear'] = {'params': None, 'performance': 0}
        
        # Test Log-linear
        try:
            res_loglinear = minimize(log_linear_fusion, [1.2, 0.1, 1.8],
                                    args=(freelook_pred, artifact_score, content_prior, target),
                                    bounds=[(0.5, 2), (0, 0.5), (0.5, 3)])
            results['log_linear'] = {
                'params': res_loglinear.x,
                'performance': -res_loglinear.fun
            }
        except Exception as e:
            logger.warning(f"Log-linear fusion failed: {e}")
            results['log_linear'] = {'params': None, 'performance': 0}
        
        # Test Exponential
        try:
            def exp_fusion(params, P_f, A, P_C, target):
                alpha, beta, gamma = params
                P_f = np.clip(P_f, 1e-10, 1)
                A = np.clip(A, 1e-10, 1)
                P_C = np.clip(P_C, 1e-10, 1)
                
                log_pred = alpha * np.log(P_f) + beta * np.log(A) + gamma * np.log(P_C)
                pred = np.exp(log_pred)
                pred = np.clip(pred, 0, 1)
                
                if np.any(np.isnan(pred)):
                    return 1e10
                
                cc = np.corrcoef(pred, target)[0, 1]
                return -cc if not np.isnan(cc) else 1e10
            
            res_exp = minimize(exp_fusion, [0.5, 0.1, 0.5],
                              args=(freelook_pred, artifact_score, content_prior, target),
                              bounds=[(0, 1), (0, 0.5), (0, 1)])
            results['exponential'] = {
                'params': res_exp.x,
                'performance': -res_exp.fun
            }
        except Exception as e:
            logger.warning(f"Exponential fusion failed: {e}")
            results['exponential'] = {'params': None, 'performance': 0}
        
        return results
    
    def parameter_sensitivity_analysis(self, freelook_pred: np.ndarray,
                                      artifact_score: np.ndarray,
                                      content_prior: np.ndarray,
                                      target: np.ndarray,
                                      base_params: Tuple = (1.2, 0.1, 1.8)) -> Dict:
        """Analyze sensitivity of parameters alpha, beta, gamma"""
        
        results = {
            'alpha_sensitivity': [],
            'beta_sensitivity': [],
            'gamma_sensitivity': []
        }
        
        # Test alpha variation
        for alpha in np.linspace(0.5, 2.0, 20):
            beta, gamma = base_params[1], base_params[2]
            pred = (freelook_pred ** alpha) * (artifact_score ** beta) * (content_prior ** gamma)
            pred = np.clip(pred, 0, 1)
            cc = np.corrcoef(pred, target)[0, 1]
            if not np.isnan(cc):
                results['alpha_sensitivity'].append({'param': alpha, 'cc': cc})
        
        # Test beta variation
        for beta in np.linspace(0, 0.3, 20):
            alpha, gamma = base_params[0], base_params[2]
            pred = (freelook_pred ** alpha) * (artifact_score ** beta) * (content_prior ** gamma)
            pred = np.clip(pred, 0, 1)
            cc = np.corrcoef(pred, target)[0, 1]
            if not np.isnan(cc):
                results['beta_sensitivity'].append({'param': beta, 'cc': cc})
        
        # Test gamma variation
        for gamma in np.linspace(0.5, 3.0, 20):
            alpha, beta = base_params[0], base_params[1]
            pred = (freelook_pred ** alpha) * (artifact_score ** beta) * (content_prior ** gamma)
            pred = np.clip(pred, 0, 1)
            cc = np.corrcoef(pred, target)[0, 1]
            if not np.isnan(cc):
                results['gamma_sensitivity'].append({'param': gamma, 'cc': cc})
        
        return results


class FailureCaseAnalysis:
    """Identify and analyze failure cases"""
    
    def __init__(self):
        pass
    
    def identify_worst_contents(self, rq2_data: pd.DataFrame, method: str = 'tas_cc', 
                               top_n: int = 5) -> pd.DataFrame:
        """Find contents where method performs worst"""
        grouped = rq2_data.groupby('content')[method].agg(['mean', 'std', 'min', 'max', 'count'])
        worst = grouped.nsmallest(top_n, 'mean')
        return worst
    
    def identify_best_contents(self, rq2_data: pd.DataFrame, method: str = 'tas_cc',
                              top_n: int = 5) -> pd.DataFrame:
        """Find contents where method performs best"""
        grouped = rq2_data.groupby('content')[method].agg(['mean', 'std', 'min', 'max', 'count'])
        best = grouped.nlargest(top_n, 'mean')
        return best
    
    def generate_failure_report(self, rq2_data: pd.DataFrame, rq1_data: pd.DataFrame) -> pd.DataFrame:
        """Generate comprehensive failure analysis report"""
        
        failure_info = []
        
        worst_tas = self.identify_worst_contents(rq2_data, 'tas_cc', top_n=10)
        best_tas = self.identify_best_contents(rq2_data, 'tas_cc', top_n=10)
        
        for content in worst_tas.index:
            content_rq1 = rq1_data[rq1_data['content'] == content]
            
            failure_info.append({
                'content': content,
                'tas_mean': worst_tas.loc[content, 'mean'],
                'tas_std': worst_tas.loc[content, 'std'],
                'tas_min': worst_tas.loc[content, 'min'],
                'num_levels': worst_tas.loc[content, 'count'],
                'avg_cc_shift': content_rq1['cc'].std(),
                'avg_jsd': content_rq1['jsd'].mean(),
                'category': 'worst'
            })
        
        return pd.DataFrame(failure_info)
