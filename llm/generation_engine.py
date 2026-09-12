"""
SAR Generation Engine
Generates SAR narratives from RAG context
"""
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from llm.loader import LLMLoader
from rag.pipeline import RAGContext
from services.prompt_updater import PromptUpdater


@dataclass
class GenerationResult:
    """Result of SAR narrative generation"""
    narrative: str
    validationstatus: str = "VALID"
    validationerrors: List[str] = field(default_factory=list)
    tokencount: int = 0
    generationtimeseconds: float = 0.0
    reasoningsteps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SARGenerationEngine:
    """
    Generates SAR narratives from RAG context

    Features:
    - Uses enhanced prompts with learned rules
    - Validates generated narratives
    - Tracks generation metrics
    """

    def __init__(self, llm_loader: LLMLoader = None, db_path: str = None):
        self.llm_loader = llm_loader or LLMLoader()
        self.prompt_updater = PromptUpdater(db_path)

        print("SAR Generation Engine initialized")

    def generate(self, rag_context: RAGContext) -> GenerationResult:
        """
        Generate SAR narrative from RAG context

        Args:
            rag_context: Retrieved context for the alert

        Returns:
            GenerationResult with narrative and metadata
        """
        start_time = time.time()
        print(f"Generation Engine: Building prompt for alert {rag_context.alert_id}")

        prompt = self._build_prompt(rag_context)
        print(f"Generation Engine: Prompt built ({len(prompt)} chars), calling LLM...")

        narrative = self.llm_loader.generate(prompt)
        generation_time = time.time() - start_time

        print(f"Generation Engine: LLM returned {len(narrative)} chars in {generation_time:.2f}s")

        validation_status, validation_errors = self._validate_narrative(narrative)

        result = GenerationResult(
            narrative=narrative,
            validationstatus=validation_status,
            validationerrors=validation_errors,
            tokencount=len(narrative.split()),
            generationtimeseconds=round(generation_time, 2),
            reasoningsteps=self._extract_reasoning_steps(narrative),
            metadata={
                "model": self.llm_loader.model_name,
                "generation_method": "HuggingFace Inference API" if self.llm_loader.use_api else "Local",
                "alert_id": rag_context.alert_id,
                "pattern_type": rag_context.metadata.get("pattern_type", "Unknown")
            }
        )

        return result

    def _build_prompt(self, rag_context: RAGContext) -> str:
        """Build the complete prompt for SAR generation"""
        system_prompt = self.prompt_updater.get_current_prompt()

        customer = rag_context.customerprofile
        txn = rag_context.transactionsummary
        metadata = rag_context.metadata
        knowledge = rag_context.retrievedknowledge

        context_text = f"""
ALERT INFORMATION:
- Alert ID: {rag_context.alert_id}
- Pattern Type: {metadata.get('pattern_type', 'Unknown')}
- Risk Score: {metadata.get('alert_risk_score', 'N/A')}
- Priority: {metadata.get('priority', 'N/A')}

CUSTOMER PROFILE:
- Name: {customer.get('name', 'Unknown')}
- Occupation: {customer.get('occupation', 'Unknown')}
- Annual Income: Rs {customer.get('annual_income_inr', 0):,}
- Risk Rating: {customer.get('risk_rating', 'Unknown')}
- PEP Status: {customer.get('pep_flag', 'No')}
- KYC Status: {customer.get('kyc_status', 'Unknown')}
- Account Type: {customer.get('account_type', 'Unknown')}
- City: {customer.get('city', 'Unknown')}

TRANSACTION SUMMARY:
- Total Transactions: {txn.get('count', 0)}
- Total Amount: Rs {txn.get('total_amount', 0):,.2f}
- Average Amount: Rs {txn.get('avg_amount', 0):,.2f}
- Maximum Amount: Rs {txn.get('max_amount', 0):,.2f}
- Period: {txn.get('startdate', 'N/A')} to {txn.get('enddate', 'N/A')}
- Channels Used: {txn.get('channel_count', 0)}
- Income Ratio: {txn.get('income_ratio', 0)}x monthly income

RELEVANT REGULATORY KNOWLEDGE:
"""
        for k in knowledge[:3]:
            context_text += f"- [{k.get('source', 'Unknown')}]: {k.get('content', '')}\n"

        task_instruction = """
Generate a complete SAR (Suspicious Activity Report) narrative with the following sections:

[SUBJECT IDENTIFICATION]
Identify the subject with full details from the customer profile.

[ACTIVITY SUMMARY]
Describe the suspicious transactions with specific amounts, dates, and channels.

[SUSPICION RATIONALE]
Explain WHY this activity is suspicious, citing specific data points and thresholds.

[REGULATORY REFERENCES]
Cite applicable PMLA sections, RBI guidelines, and FIU-IND requirements.

[CONCLUSION]
State the filing recommendation and required actions.

IMPORTANT:
- Use ONLY facts from the provided context
- Be specific with numbers and dates
- Use formal, objective language
- Do NOT make up any information
"""

        full_prompt = f"""{system_prompt}

{context_text}

{task_instruction}

SAR NARRATIVE:
"""
        return full_prompt

    def _validate_narrative(self, narrative: str) -> tuple:
        """Validate the generated narrative"""
        required_sections = [
            "SUBJECT IDENTIFICATION",
            "ACTIVITY SUMMARY",
            "SUSPICION RATIONALE",
            "REGULATORY REFERENCES",
            "CONCLUSION"
        ]

        errors = []
        for section in required_sections:
            if section not in narrative.upper():
                errors.append(f"Missing section: {section}")

        if not any(reg in narrative.upper() for reg in ["PMLA", "FIU", "RBI"]):
            errors.append("No regulatory references found")

        status = "VALID" if not errors else "NEEDS_REVIEW"
        return status, errors

    def _extract_reasoning_steps(self, narrative: str) -> List[str]:
        """Extract reasoning steps from narrative"""
        steps = []

        if "SUBJECT IDENTIFICATION" in narrative.upper():
            steps.append("Identified subject from customer profile")
        if "ACTIVITY SUMMARY" in narrative.upper():
            steps.append("Summarized suspicious transactions")
        if "SUSPICION RATIONALE" in narrative.upper():
            steps.append("Explained suspicion indicators")
        if "REGULATORY REFERENCES" in narrative.upper():
            steps.append("Cited regulatory framework")
        if "CONCLUSION" in narrative.upper():
            steps.append("Provided filing recommendation")

        return steps
