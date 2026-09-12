"""
Data models and Pydantic schemas for SAR Generation System
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pydantic import BaseModel, Field


# ============================================================
# DATACLASS MODELS (Track C Learning System)
# ============================================================

@dataclass
class FeedbackEntry:
    """
    Stores details about an analyst's edits to a generated SAR
    """
    feedback_id: str
    alert_id: str
    alert_type: str
    generation_id: str
    original_narrative: str
    edited_narrative: str
    diff_added: List[str] = field(default_factory=list)
    diff_removed: List[str] = field(default_factory=list)
    diff_changed: List[Dict[str, str]] = field(default_factory=list)
    edit_count: int = 0
    edit_distance: int = 0
    section_edits: Dict[str, Any] = field(default_factory=dict)
    analyst_id: str = "UNKNOWN"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    approval_status: str = "PENDING"
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_db_tuple(self) -> tuple:
        return (
            self.feedback_id,
            self.alert_id,
            self.alert_type,
            self.generation_id,
            self.original_narrative,
            self.edited_narrative,
            json.dumps(self.diff_added),
            json.dumps(self.diff_removed),
            json.dumps(self.diff_changed),
            self.edit_count,
            self.edit_distance,
            json.dumps(self.section_edits),
            self.analyst_id,
            self.timestamp,
            self.approval_status,
            self.quality_score,
            json.dumps(self.metadata)
        )


@dataclass
class LearnedPattern:
    """
    A systematic improvement detected from multiple feedbacks
    """
    pattern_id: str
    pattern_name: str
    pattern_type: str  # MISSING_INFO, TERMINOLOGY, STRUCTURE, TONE
    description: str
    rule_instruction: str
    confidence_score: float
    frequency: int
    total_samples: int
    occurrence_rate: float
    alert_types: List[str] = field(default_factory=list)
    example_feedbacks: List[str] = field(default_factory=list)
    first_detected: str = field(default_factory=lambda: datetime.now().isoformat())
    last_confirmed: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "PENDING"  # PENDING, ACTIVE, DEPRECATED
    impact_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_db_tuple(self) -> tuple:
        return (
            self.pattern_id,
            self.pattern_name,
            self.pattern_type,
            self.description,
            self.rule_instruction,
            self.confidence_score,
            self.frequency,
            self.total_samples,
            self.occurrence_rate,
            json.dumps(self.alert_types),
            json.dumps(self.example_feedbacks),
            self.first_detected,
            self.last_confirmed,
            self.status,
            json.dumps(self.impact_metrics),
            json.dumps(self.metadata)
        )


@dataclass
class ExperienceEntry:
    """
    A successful SAR that can be reused as an example
    """
    experience_id: str
    alert_id: str
    alert_type: str
    quality_score: float
    edit_count: int
    approved_narrative: str
    rag_context: Dict[str, Any]
    customer_profile_summary: str
    transaction_pattern_summary: str
    key_features: Dict[str, float]
    analyst_id: str
    approval_date: str = field(default_factory=lambda: datetime.now().isoformat())
    usage_count: int = 0
    last_used: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_db_tuple(self) -> tuple:
        return (
            self.experience_id,
            self.alert_id,
            self.alert_type,
            self.quality_score,
            self.edit_count,
            self.approved_narrative,
            json.dumps(self.rag_context),
            self.customer_profile_summary,
            self.transaction_pattern_summary,
            json.dumps(self.key_features),
            self.analyst_id,
            self.approval_date,
            self.usage_count,
            self.last_used,
            json.dumps(self.metadata)
        )


@dataclass
class PromptVersion:
    """
    A version of the system prompt with learned rules applied
    """
    version: str
    prompt_text: str
    rules_applied: List[str]
    changes_from_previous: str
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "system"
    ab_test_results: Dict[str, Any] = field(default_factory=dict)
    deployment_date: Optional[str] = None
    previous_version: Optional[str] = None
    status: str = "TESTING"  # TESTING, ACTIVE, DEPRECATED
    notes: str = ""

    def to_db_tuple(self) -> tuple:
        return (
            self.version,
            self.prompt_text,
            json.dumps(self.rules_applied),
            self.changes_from_previous,
            self.created_date,
            self.created_by,
            json.dumps(self.ab_test_results),
            self.deployment_date,
            self.previous_version,
            self.status,
            self.notes
        )


@dataclass
class LearningMetric:
    """
    A single metric measurement at a point in time
    """
    metric_id: str
    metric_type: str  # EDIT_COUNT, APPROVAL_RATE, PATTERN_COMPLIANCE, etc.
    metric_value: float
    sar_count: int
    window_start: str
    window_end: str
    prompt_version: str
    alert_type: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_db_tuple(self) -> tuple:
        return (
            self.metric_id,
            self.metric_type,
            self.metric_value,
            self.sar_count,
            self.window_start,
            self.window_end,
            self.prompt_version,
            self.alert_type,
            self.timestamp,
            json.dumps(self.metadata)
        )


# ============================================================
# PYDANTIC MODELS (API Request/Response)
# ============================================================

class GenerateSARRequest(BaseModel):
    alertid: str
    analystid: str
    usehybrid: bool = True
    usereranking: bool = True


class ApproveSARRequest(BaseModel):
    sarid: str
    analystid: str
    editednarrative: Dict[str, str]
    approvalstatus: str
    comments: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class SARGenerationResponse(BaseModel):
    sarid: str
    alertid: str
    narrative: Dict[str, str]
    metadata: Dict[str, Any]
    validationstatus: str
    generationtimeseconds: float
    auditid: str
    status: str


class ApprovalResponse(BaseModel):
    status: str
    sarid: str
    learningtriggered: bool
    message: str
