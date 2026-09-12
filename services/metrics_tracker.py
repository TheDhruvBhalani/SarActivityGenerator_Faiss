"""
Component 5: Metrics Dashboard
Tracks and visualizes learning improvement over time
"""
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

from config.settings import Config
from models.schemas import LearningMetric
from services.feedback_collector import FeedbackCollector
from services.pattern_extractor import PatternExtractor


class MetricsDashboard:
    """
    Tracks and visualizes learning metrics

    How it works:
    1. Records metrics after each SAR (edit count, approval rate, etc.)
    2. Calculates trends over time
    3. Generates visualizations (learning curves, pattern compliance)
    4. Provides ROI insights
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.TRACK_C_DB_PATH

    def record_metric(
        self,
        metric_type: str,
        metric_value: float,
        sar_count: int,
        prompt_version: str = "v1.0",
        alert_type: Optional[str] = None
    ):
        """Record a single metric measurement"""
        metric = LearningMetric(
            metric_id=f"METRIC_{metric_type}_{sar_count}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            metric_type=metric_type,
            metric_value=metric_value,
            sar_count=sar_count,
            window_start=datetime.now().isoformat(),
            window_end=datetime.now().isoformat(),
            prompt_version=prompt_version,
            alert_type=alert_type
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO learning_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', metric.to_db_tuple())

        conn.commit()
        conn.close()

    def calculate_average_edits(self, window_size: int = 10) -> float:
        """Calculate average edit count over recent SARs"""
        collector = FeedbackCollector(self.db_path)
        feedbacks = collector.get_all_feedbacks()

        if not feedbacks:
            return 0.0

        recent = feedbacks[:window_size]
        avg_edits = sum(f.edit_count for f in recent) / len(recent)
        return round(avg_edits, 2)

    def calculate_approval_rate(self, window_size: int = 10) -> float:
        """Calculate percentage of SARs approved with <=2 edits"""
        collector = FeedbackCollector(self.db_path)
        feedbacks = collector.get_all_feedbacks()

        if not feedbacks:
            return 0.0

        recent = feedbacks[:window_size]
        approved_count = sum(1 for f in recent if f.edit_count <= 2)
        rate = approved_count / len(recent)

        return round(rate, 3)

    def calculate_pattern_compliance(self, pattern_id: str) -> float:
        """Calculate how often a specific learned pattern is being followed"""
        return 0.85  # Placeholder

    def get_learning_curve_data(self) -> pd.DataFrame:
        """Get time-series data for learning curve visualization"""
        conn = sqlite3.connect(self.db_path)

        query = '''
            SELECT sar_count, metric_value, timestamp
            FROM learning_metrics
            WHERE metric_type = 'EDIT_COUNT'
            ORDER BY sar_count
        '''

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df

    def plot_learning_curve(self, save_path: Optional[str] = None):
        """Visualize how average edits decrease over time"""
        df = self.get_learning_curve_data()

        if df.empty:
            print("No learning curve data available yet")
            return

        plt.figure(figsize=(12, 6))

        plt.plot(df['sar_count'], df['metric_value'],
                marker='o', linewidth=2, markersize=8,
                color='#2E86AB', label='Average Edits per SAR')

        z = np.polyfit(df['sar_count'], df['metric_value'], 2)
        p = np.poly1d(z)
        plt.plot(df['sar_count'], p(df['sar_count']),
                "--", color='#A23B72', linewidth=2,
                label='Trend Line', alpha=0.7)

        plt.xlabel('Number of SARs Generated', fontsize=12, fontweight='bold')
        plt.ylabel('Average Edits per SAR', fontsize=12, fontweight='bold')
        plt.title('Track C Learning Curve: System Improvement Over Time',
                 fontsize=14, fontweight='bold', pad=20)

        if len(df) > 1:
            first_value = df['metric_value'].iloc[0]
            last_value = df['metric_value'].iloc[-1]
            improvement = ((first_value - last_value) / first_value) * 100

            plt.text(0.02, 0.98,
                    f'Improvement: {improvement:.1f}%\n'
                    f'Initial: {first_value:.1f} edits\n'
                    f'Current: {last_value:.1f} edits',
                    transform=plt.gca().transAxes,
                    fontsize=11,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.grid(True, alpha=0.3)
        plt.legend(loc='upper right', fontsize=11)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Learning curve saved to {save_path}")

        plt.show()

    def plot_pattern_compliance(self, save_path: Optional[str] = None):
        """Shows how well the system follows learned patterns over time"""
        extractor = PatternExtractor(self.db_path)
        patterns = extractor.get_active_patterns()

        if not patterns:
            print("No active patterns to display")
            return

        pattern_names = [p.pattern_name[:30] + '...' if len(p.pattern_name) > 30 else p.pattern_name
                        for p in patterns[:5]]
        compliance_rates = [p.confidence_score * 100 for p in patterns[:5]]
        frequencies = [p.frequency for p in patterns[:5]]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        colors = ['#06A77D' if rate >= 75 else '#F77F00' if rate >= 60 else '#EF233C'
                 for rate in compliance_rates]

        bars1 = ax1.barh(pattern_names, compliance_rates, color=colors, alpha=0.8)
        ax1.set_xlabel('Compliance Rate (%)', fontsize=11, fontweight='bold')
        ax1.set_title('Pattern Compliance Rates', fontsize=12, fontweight='bold')
        ax1.axvline(x=75, color='green', linestyle='--', alpha=0.5, label='Target: 75%')

        for i, (bar, val) in enumerate(zip(bars1, compliance_rates)):
            ax1.text(val + 2, bar.get_y() + bar.get_height()/2,
                    f'{val:.0f}%', va='center', fontsize=10, fontweight='bold')

        ax1.legend()
        ax1.set_xlim(0, 110)

        bars2 = ax2.barh(pattern_names, frequencies, color='#2E86AB', alpha=0.8)
        ax2.set_xlabel('Frequency (Times Detected)', fontsize=11, fontweight='bold')
        ax2.set_title('Pattern Detection Frequency', fontsize=12, fontweight='bold')

        for bar, val in zip(bars2, frequencies):
            ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                    f'{val}', va='center', fontsize=10, fontweight='bold')

        plt.suptitle('Learned Patterns Performance',
                    fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Pattern compliance saved to {save_path}")

        plt.show()

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report"""
        collector = FeedbackCollector(self.db_path)
        extractor = PatternExtractor(self.db_path)

        feedbacks = collector.get_all_feedbacks()
        patterns = extractor.get_active_patterns()

        total_sars = len(feedbacks)
        avg_edits = self.calculate_average_edits(window_size=min(10, total_sars))
        approval_rate = self.calculate_approval_rate(window_size=min(10, total_sars))

        if total_sars >= 10:
            first_10 = feedbacks[-10:]
            last_10 = feedbacks[:10]

            first_avg = sum(f.edit_count for f in first_10) / len(first_10)
            last_avg = sum(f.edit_count for f in last_10) / len(last_10)

            improvement_pct = ((first_avg - last_avg) / first_avg * 100) if first_avg > 0 else 0
        else:
            improvement_pct = 0

        report = {
            "total_sars_processed": total_sars,
            "avg_edits_current": avg_edits,
            "approval_rate": approval_rate,
            "improvement_percentage": round(improvement_pct, 1),
            "patterns_learned": len(patterns),
            "active_patterns": [p.pattern_name for p in patterns],
            "avg_quality_score": round(sum(f.quality_score for f in feedbacks) / len(feedbacks), 1) if feedbacks else 0
        }

        return report

    def print_summary_report(self):
        """Print a nice formatted summary report"""
        report = self.generate_summary_report()

        print("\n" + "="*80)
        print("TRACK C LEARNING SYSTEM - PERFORMANCE SUMMARY")
        print("="*80)

        print(f"\nOVERALL METRICS:")
        print(f"   Total SARs Processed: {report['total_sars_processed']}")
        print(f"   Current Avg Edits: {report['avg_edits_current']}")
        print(f"   First-Pass Approval Rate: {report['approval_rate']:.1%}")
        print(f"   Average Quality Score: {report['avg_quality_score']}/100")

        print(f"\nIMPROVEMENT:")
        print(f"   Edit Reduction: {report['improvement_percentage']:.1f}%")

        print(f"\nLEARNING:")
        print(f"   Patterns Discovered: {report['patterns_learned']}")
        if report['active_patterns']:
            print(f"   Active Patterns:")
            for i, pattern in enumerate(report['active_patterns'][:5], 1):
                print(f"     {i}. {pattern}")

        print("\n" + "="*80)
