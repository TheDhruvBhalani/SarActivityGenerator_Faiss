"""
Continual Learning Engine
Complete Track C system integrating all 5 components
"""
from datetime import datetime
from typing import Dict, Any, Optional

from config.settings import Config
from services.feedback_collector import FeedbackCollector
from services.pattern_extractor import PatternExtractor
from services.experience_replay import ExperienceReplay
from services.prompt_updater import PromptUpdater
from services.metrics_tracker import MetricsDashboard


class ContinualLearningEngine:
    """
    Complete Track C system integrating all 5 components

    Usage:
        engine = ContinualLearningEngine()
        engine.process_feedback(alert_id, original, edited, ...)
        engine.get_enhanced_prompt()
        engine.show_learning_metrics()
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.TRACK_C_DB_PATH

        self.feedback_collector = FeedbackCollector(self.db_path)
        self.pattern_extractor = PatternExtractor(self.db_path)
        self.experience_replay = ExperienceReplay(self.db_path)
        self.prompt_updater = PromptUpdater(self.db_path)
        self.metrics_dashboard = MetricsDashboard(self.db_path)

        print("Continual Learning Engine initialized!")
        print("   All 5 components loaded and ready")

    def process_feedback(
        self,
        alert_id: str,
        alert_type: str,
        generation_id: str,
        original_narrative: str,
        edited_narrative: str,
        rag_context: Dict[str, Any],
        analyst_id: str = "ANALYST_001",
        approval_status: str = "APPROVED"
    ) -> Dict[str, Any]:
        """
        Main method: Process analyst feedback through the learning pipeline

        Steps:
        1. Collect feedback (Component 1)
        2. Check if new patterns emerged (Component 2)
        3. Add to experience library if high quality (Component 3)
        4. Update prompt if patterns detected (Component 4)
        5. Record metrics (Component 5)
        """
        print(f"\n{'='*80}")
        print(f"PROCESSING FEEDBACK FOR: {alert_id}")
        print(f"{'='*80}")

        # Step 1: Collect Feedback
        print("\n[1/5] Collecting feedback...")
        feedback = self.feedback_collector.collect_feedback(
            alert_id=alert_id,
            alert_type=alert_type,
            generation_id=generation_id,
            original_narrative=original_narrative,
            edited_narrative=edited_narrative,
            analyst_id=analyst_id,
            approval_status=approval_status
        )
        print(f"   Feedback collected (ID: {feedback.feedback_id})")
        print(f"   Edit count: {feedback.edit_count}")
        print(f"   Quality score: {feedback.quality_score}/100")

        # Step 2: Extract Patterns
        all_feedbacks = self.feedback_collector.get_all_feedbacks()
        new_patterns = []

        if len(all_feedbacks) % 5 == 0:
            print("\n[2/5] Extracting patterns...")
            new_patterns = self.pattern_extractor.extract_patterns(
                min_frequency=3,
                min_confidence=0.6
            )
            if new_patterns:
                print(f"   Detected {len(new_patterns)} new patterns!")
            else:
                print(f"   No new patterns detected yet")
        else:
            print(f"\n[2/5] Pattern extraction skipped (waiting for more data)")

        # Step 3: Add to Experience Library
        print("\n[3/5] Updating experience library...")
        experience = None
        if approval_status == "APPROVED" and feedback.quality_score >= 70:
            experience = self.experience_replay.add_experience(
                alert_id=alert_id,
                alert_type=alert_type,
                approved_narrative=edited_narrative,
                rag_context=rag_context,
                edit_count=feedback.edit_count,
                analyst_id=analyst_id
            )
            if experience:
                print(f"   Added to experience library!")
        else:
            print(f"   Not added (quality below threshold)")

        # Step 4: Update Prompt
        print("\n[4/5] Checking prompt updates...")
        prompt_update = None
        if new_patterns:
            prompt_update = self.prompt_updater.generate_updated_prompt()
            if prompt_update:
                print(f"   New prompt version created: {prompt_update.version}")

        # Step 5: Record Metrics
        print("\n[5/5] Recording metrics...")
        self.metrics_dashboard.record_metric(
            metric_type="EDIT_COUNT",
            metric_value=feedback.edit_count,
            sar_count=len(all_feedbacks),
            prompt_version="v1.0"
        )
        print(f"   Metrics recorded")

        print(f"\n{'='*80}")
        print(f"FEEDBACK PROCESSING COMPLETE")
        print(f"{'='*80}")

        return {
            "feedback": feedback,
            "new_patterns": len(new_patterns),
            "experience_added": experience is not None,
            "prompt_updated": prompt_update is not None,
            "total_sars": len(all_feedbacks)
        }

    def get_enhanced_prompt(self, alert_type: Optional[str] = None) -> str:
        """Get the current enhanced prompt with learned rules"""
        return self.prompt_updater.get_current_prompt()

    def get_similar_experience(
        self,
        alert_type: str,
        rag_context: Dict[str, Any]
    ) -> Optional[str]:
        """Get a similar past SAR as a few-shot example"""
        experiences = self.experience_replay.find_similar_experience(
            alert_type=alert_type,
            rag_context=rag_context,
            top_k=1
        )

        if experiences:
            self.experience_replay.update_usage(experiences[0].experience_id)
            return experiences[0].approved_narrative

        return None

    def show_learning_metrics(self):
        """Display learning metrics dashboard"""
        self.metrics_dashboard.print_summary_report()

    def plot_learning_progress(self, save_path: Optional[str] = None):
        """Plot learning curve visualization"""
        self.metrics_dashboard.plot_learning_curve(save_path)

    def plot_pattern_compliance(self, save_path: Optional[str] = None):
        """Plot pattern compliance visualization"""
        self.metrics_dashboard.plot_pattern_compliance(save_path)
