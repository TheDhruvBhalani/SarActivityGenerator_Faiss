"""
Feedback and Learning Endpoints
"""
from typing import Dict

from fastapi import APIRouter, Depends

from api.auth import require_permission
from services.continual_learning_engine import ContinualLearningEngine

router = APIRouter(tags=["Feedback"])

learning_engine = None


def get_learning_engine() -> ContinualLearningEngine:
    """Get or create learning engine singleton"""
    global learning_engine
    if learning_engine is None:
        learning_engine = ContinualLearningEngine()
    return learning_engine


@router.get("/api/v1/learning/metrics")
async def get_learning_metrics(
    user: Dict = Depends(require_permission("viewaudit"))
):
    """Get learning metrics summary"""
    engine = get_learning_engine()
    report = engine.metrics_dashboard.generate_summary_report()
    return {"status": "success", "metrics": report}


@router.get("/api/v1/learning/patterns")
async def get_learned_patterns(
    user: Dict = Depends(require_permission("viewaudit"))
):
    """Get active learned patterns"""
    engine = get_learning_engine()
    patterns = engine.pattern_extractor.get_active_patterns()
    return {
        "status": "success",
        "count": len(patterns),
        "patterns": [
            {
                "id": p.pattern_id,
                "name": p.pattern_name,
                "type": p.pattern_type,
                "confidence": p.confidence_score,
                "frequency": p.frequency,
                "rule": p.rule_instruction
            }
            for p in patterns
        ]
    }


@router.get("/api/v1/learning/prompt")
async def get_current_prompt(
    user: Dict = Depends(require_permission("viewaudit"))
):
    """Get current enhanced prompt"""
    engine = get_learning_engine()
    prompt = engine.prompt_updater.get_current_prompt()
    return {"status": "success", "prompt": prompt}
