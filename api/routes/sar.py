"""
SAR Generation and Approval Endpoints
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from config.settings import APIConfig
from models.schemas import (
    GenerateSARRequest,
    ApproveSARRequest,
    SARGenerationResponse,
    ApprovalResponse,
    UserLogin,
    TokenResponse
)
from api.auth import AuthManager, require_permission
from rag.pipeline import RAGPipeline
from llm.loader import LLMLoader
from llm.generation_engine import SARGenerationEngine
from services.continual_learning_engine import ContinualLearningEngine
from utils.helpers import AuditLogger, LogicAuditTrail

router = APIRouter(tags=["SAR"])


class OrchestrationService:
    """Orchestrates SAR generation workflow"""

    def __init__(self):
        self.rag_pipeline = RAGPipeline()
        self.llm_loader = LLMLoader()
        self.generation_engine = SARGenerationEngine(self.llm_loader)
        self.learning_engine = ContinualLearningEngine()
        print("Orchestration service ready")

    async def generate_sar(
        self,
        alert_id: str,
        analyst_id: str,
        use_hybrid: bool = True,
        use_reranking: bool = True,
        user: Optional[Dict] = None
    ) -> SARGenerationResponse:
        """Generate SAR for alert"""
        start_time = datetime.now()

        LogicAuditTrail.init_trail(alert_id, user)
        AuditLogger.log_event("SAR_GENERATION_STARTED", {"alert_id": alert_id}, user)

        try:
            LogicAuditTrail.log_step(alert_id, "ALERT_INGESTION", {
                "status": "COMPLETED",
                "alert_id": alert_id,
                "initiated_by": analyst_id
            })

            rag_context = self.rag_pipeline.process_alert(
                alert_id, use_hybrid, use_reranking
            )

            LogicAuditTrail.log_step(alert_id, "RAG_RETRIEVAL", {
                "status": "COMPLETED",
                "customer": rag_context.customerprofile.get("name"),
                "txn_count": rag_context.transactionsummary.get("count"),
                "knowledge_chunks": len(rag_context.retrievedknowledge)
            })

            gen_result = self.generation_engine.generate(rag_context)

            LogicAuditTrail.log_step(alert_id, "LLM_GENERATION", {
                "status": "COMPLETED",
                "tokens": gen_result.tokencount,
                "time_seconds": gen_result.generationtimeseconds
            })

            LogicAuditTrail.log_step(alert_id, "VALIDATION", {
                "status": "COMPLETED",
                "validation_status": gen_result.validationstatus,
                "errors": gen_result.validationerrors
            })

            sar_id = f"SAR-{alert_id}-{int(datetime.now().timestamp())}"

            sar_data = {
                "sarid": sar_id,
                "alertid": alert_id,
                "narrative": {"fulltext": gen_result.narrative},
                "metadata": gen_result.metadata,
                "validationstatus": gen_result.validationstatus,
                "analystid": analyst_id,
                "generationtimeseconds": (datetime.now() - start_time).total_seconds()
            }

            self._save_sar(sar_data)
            LogicAuditTrail.finalize_trail(alert_id, sar_id)
            AuditLogger.log_event("SAR_GENERATION_COMPLETED", {"sar_id": sar_id}, user)

            return SARGenerationResponse(
                sarid=sar_id,
                alertid=alert_id,
                narrative={"fulltext": gen_result.narrative},
                metadata=gen_result.metadata,
                validationstatus=gen_result.validationstatus,
                generationtimeseconds=(datetime.now() - start_time).total_seconds(),
                auditid=f"AUDIT-{sar_id}",
                status="success"
            )

        except Exception as e:
            LogicAuditTrail.log_step(alert_id, "ERROR", {
                "status": "FAILED",
                "error": str(e)
            })
            AuditLogger.log_event("SAR_GENERATION_ERROR", {"error": str(e)}, user)
            raise HTTPException(status_code=500, detail=f"SAR generation failed: {e}")

    async def approve_sar(
        self,
        sar_id: str,
        analyst_id: str,
        edited_narrative: Dict[str, str],
        approval_status: str,
        comments: Optional[str] = None,
        user: Optional[Dict] = None
    ) -> ApprovalResponse:
        """Approve or reject SAR"""
        alert_id = sar_id.split("-")[1] if "-" in sar_id else "UNKNOWN"

        self._update_sar_approval(sar_id, {
            "approvalstatus": approval_status,
            "analystid": analyst_id
        })

        learning_triggered = False
        if approval_status == "APPROVED":
            learning_triggered = True

        AuditLogger.log_event("SAR_APPROVED", {
            "sarid": sar_id,
            "status": approval_status,
            "approved_by": analyst_id
        }, user)

        return ApprovalResponse(
            status="success",
            sarid=sar_id,
            learningtriggered=learning_triggered,
            message=f"SAR {approval_status.lower()} successfully"
        )

    def _save_sar(self, sar_data: Dict):
        """Save generated SAR to file"""
        try:
            os.makedirs(APIConfig.GENERATED_NARRATIVES_DIR, exist_ok=True)
            filepath = os.path.join(
                APIConfig.GENERATED_NARRATIVES_DIR,
                f"{sar_data['sarid']}.json"
            )
            with open(filepath, "w") as f:
                json.dump(sar_data, f, indent=2)
        except Exception as e:
            logging.error(f"Save SAR failed: {e}")

    def _update_sar_approval(self, sar_id: str, data: Dict):
        """Update SAR approval status"""
        try:
            filepath = os.path.join(
                APIConfig.GENERATED_NARRATIVES_DIR,
                f"{sar_id}.json"
            )
            if os.path.exists(filepath):
                with open(filepath) as f:
                    sar = json.load(f)
                sar["approvalstatus"] = data.get("approvalstatus")
                sar["approved_by"] = data.get("analystid")
                sar["approved_at"] = datetime.now().isoformat()
                with open(filepath, "w") as f:
                    json.dump(sar, f, indent=2)
        except Exception as e:
            logging.error(f"Update SAR approval failed: {e}")


orchestrator = None
_orchestrator_initialized = False


def get_orchestrator() -> OrchestrationService:
    """Get or create orchestration service singleton"""
    global orchestrator, _orchestrator_initialized
    if orchestrator is None or not _orchestrator_initialized:
        print("Initializing fresh OrchestrationService...")
        orchestrator = OrchestrationService()
        _orchestrator_initialized = True
    return orchestrator


def reset_orchestrator():
    """Force reset orchestrator (for code reloads)"""
    global orchestrator, _orchestrator_initialized
    orchestrator = None
    _orchestrator_initialized = False


@router.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login endpoint"""
    user = AuthManager.authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = AuthManager.create_access_token({
        "sub": user["username"],
        "role": user["role"]
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        username=user["username"]
    )


@router.post("/api/v1/generate-sar", response_model=SARGenerationResponse)
async def generate_sar(
    request: GenerateSARRequest,
    user: Dict = Depends(require_permission("generatesar"))
):
    """Generate SAR for alert"""
    orch = get_orchestrator()
    return await orch.generate_sar(
        alert_id=request.alertid,
        analyst_id=request.analystid,
        use_hybrid=request.usehybrid,
        use_reranking=request.usereranking,
        user=user
    )


@router.post("/api/v1/sar/{sar_id}/approve", response_model=ApprovalResponse)
async def approve_sar(
    sar_id: str,
    request: ApproveSARRequest,
    user: Dict = Depends(require_permission("approvesar"))
):
    """Approve or reject SAR"""
    orch = get_orchestrator()
    return await orch.approve_sar(
        sar_id=sar_id,
        analyst_id=request.analystid,
        edited_narrative=request.editednarrative,
        approval_status=request.approvalstatus,
        comments=request.comments,
        user=user
    )


@router.get("/api/v1/logic-audit-trail/{alert_id}")
async def get_logic_audit_trail(
    alert_id: str,
    user: Dict = Depends(require_permission("viewaudit"))
):
    """Get audit trail for alert"""
    trail = LogicAuditTrail.get_trail(alert_id)
    if "error" in trail:
        raise HTTPException(status_code=404, detail=trail["error"])
    return {"alert_id": alert_id, "audit_trail": trail}
