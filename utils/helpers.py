"""
Utility functions and logging helpers
"""
import os
import json
import logging
import difflib
from datetime import datetime
from typing import Dict, Any, List, Optional

from config.settings import APIConfig


class AuditLogger:
    """Audit logger for tracking WHO did WHAT and WHEN"""

    @staticmethod
    def log_event(event_type: str, data: Dict[str, Any], user: Optional[Dict] = None):
        """Log an audit event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user": user.get("username") if user else "system",
            "role": user.get("role") if user else "system",
            "data": data,
        }
        try:
            os.makedirs(os.path.dirname(APIConfig.AUDIT_LOG_PATH), exist_ok=True)
            with open(APIConfig.AUDIT_LOG_PATH, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logging.error(f"AuditLogger failed: {e}")


class ExplainabilityLogger:
    """
    Logger for AI reasoning transparency.
    Every entry answers: which data -> which decision -> which output text.
    """

    @staticmethod
    def log_reasoning(
        alert_id: str,
        step: str,
        reasoning_chain: List[Dict],
        conclusion: str,
        narrative_impact: str,
        user: Optional[Dict] = None
    ):
        """Log AI reasoning for explainability"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "alert_id": alert_id,
            "step": step,
            "analyst": user.get("username") if user else "system",
            "role": user.get("role") if user else "system",
            "reasoning_chain": reasoning_chain,
            "conclusion": conclusion,
            "narrative_impact": narrative_impact,
        }
        try:
            os.makedirs(os.path.dirname(APIConfig.EXPLAIN_LOG_PATH), exist_ok=True)
            with open(APIConfig.EXPLAIN_LOG_PATH, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logging.error(f"ExplainabilityLogger failed: {e}")

    @staticmethod
    def build_threshold_check(
        data_point: str,
        value,
        threshold,
        condition: str,
        triggered: bool,
        regulation: str,
        explanation: str
    ) -> Dict:
        """Build a standard threshold check entry"""
        return {
            "data_point": data_point,
            "value": value,
            "threshold": threshold,
            "condition": condition,
            "triggered": triggered,
            "regulation": regulation,
            "explanation": explanation,
        }


class LogicAuditTrail:
    """Tracks the logic flow of SAR generation"""

    @staticmethod
    def trail_path(alert_id: str) -> str:
        """Get path for audit trail file"""
        os.makedirs(APIConfig.OUTPUT_DIR, exist_ok=True)
        return os.path.join(APIConfig.OUTPUT_DIR, f"logic-audit-{alert_id}.json")

    @staticmethod
    def init_trail(alert_id: str, user: Optional[Dict] = None) -> dict:
        """Initialize a new audit trail"""
        trail = {
            "alert_id": alert_id,
            "sar_id": None,
            "created_by": user.get("username") if user else "system",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "overall_status": "IN_PROGRESS",
            "steps": {},
        }
        try:
            with open(LogicAuditTrail.trail_path(alert_id), "w") as f:
                json.dump(trail, f, indent=2)
        except Exception as e:
            logging.error(f"LogicAuditTrail init failed: {e}")
        return trail

    @staticmethod
    def log_step(alert_id: str, step_name: str, data: dict):
        """Log a step in the audit trail"""
        path = LogicAuditTrail.trail_path(alert_id)
        try:
            trail = (json.load(open(path)) if os.path.exists(path)
                     else LogicAuditTrail.init_trail(alert_id))
            trail["steps"][step_name] = {
                "step": step_name,
                "timestamp": datetime.now().isoformat(),
                "status": data.pop("status", "COMPLETED"),
                "details": data,
            }
            trail["last_updated"] = datetime.now().isoformat()
            with open(path, "w") as f:
                json.dump(trail, f, indent=2)
        except Exception as e:
            logging.error(f"LogicAuditTrail log_step failed: {e}")

    @staticmethod
    def finalize_trail(alert_id: str, sar_id: str, overall_status: str = "COMPLETED"):
        """Finalize the audit trail"""
        path = LogicAuditTrail.trail_path(alert_id)
        try:
            trail = json.load(open(path)) if os.path.exists(path) else {}
            trail["sar_id"] = sar_id
            trail["overall_status"] = overall_status
            trail["last_updated"] = datetime.now().isoformat()
            trail["completed_steps"] = list(trail.get("steps", {}).keys())
            trail["total_steps"] = len(trail.get("steps", {}))
            with open(path, "w") as f:
                json.dump(trail, f, indent=2)
        except Exception as e:
            logging.error(f"LogicAuditTrail finalize failed: {e}")

    @staticmethod
    def get_trail(alert_id: str) -> dict:
        """Get audit trail for alert"""
        path = LogicAuditTrail.trail_path(alert_id)
        if os.path.exists(path):
            try:
                return json.load(open(path))
            except Exception as e:
                logging.error(f"LogicAuditTrail read failed: {e}")
        return {"alert_id": alert_id, "error": "No logic audit trail found"}

    @staticmethod
    def log_analyst_action(
        alert_id: str,
        action: str,
        user: str,
        original_text: str = "",
        edited_text: str = "",
        comments: str = ""
    ):
        """Log analyst action with diff analysis"""
        diff = list(difflib.unified_diff(
            original_text.splitlines(),
            edited_text.splitlines(),
            fromfile="original",
            tofile="edited",
            lineterm=""
        )) if original_text else []

        LogicAuditTrail.log_step(alert_id, "ANALYST_ACTIONS", {
            "status": "COMPLETED",
            "action": action,
            "performed_by": user,
            "analyst_comments": comments,
            "edit_summary": {
                "total_changes": len([l for l in diff if l.startswith(("+", "-"))
                                      and not l.startswith(("+++", "---"))]),
                "lines_added": len([l for l in diff if l.startswith("+") and not l.startswith("+++")]),
                "lines_removed": len([l for l in diff if l.startswith("-") and not l.startswith("---")]),
                "chars_before": len(original_text),
                "chars_after": len(edited_text),
            },
            "final_status": action,
        })
