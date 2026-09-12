"""
Configuration settings for SAR Generation System
"""
import os
from pathlib import Path


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


class Config:
    """Base configuration for paths and directories"""

    # Primary output directory (local)
    OUTPUT_DIR = str(PROJECT_ROOT / 'data' / 'output')

    # Knowledge base directories
    BASE_DIR = str(PROJECT_ROOT / 'data' / 'knowledge_base')
    KNOWLEDGE_DIR = str(PROJECT_ROOT / 'data' / 'knowledge_base' / 'documents')
    VECTOR_DB_DIR = str(PROJECT_ROOT / 'data' / 'knowledge_base' / 'faiss_db')

    # Database paths
    DB_PATH = str(PROJECT_ROOT / 'data' / 'sar_prototype.db')
    TRACK_C_DB_PATH = str(PROJECT_ROOT / 'data' / 'continual_learning.db')

    # Model training paths
    MODEL_OUTPUT_DIR = str(PROJECT_ROOT / 'data' / 'trained_models')
    SAR_MISTRAL_LORA_PATH = str(PROJECT_ROOT / 'data' / 'trained_models' / 'sar_mistral_lora')

    # Generated narratives
    GENERATED_NARRATIVES_DIR = str(PROJECT_ROOT / 'data' / 'generated_narratives')

    @classmethod
    def ensure_directories(cls):
        """Create all necessary directories"""
        directories = [
            cls.OUTPUT_DIR,
            cls.BASE_DIR,
            cls.KNOWLEDGE_DIR,
            cls.VECTOR_DB_DIR,
            cls.MODEL_OUTPUT_DIR,
            cls.GENERATED_NARRATIVES_DIR,
            f'{cls.KNOWLEDGE_DIR}/templates',
            f'{cls.KNOWLEDGE_DIR}/typologies',
            f'{cls.KNOWLEDGE_DIR}/regulations',
            f'{cls.KNOWLEDGE_DIR}/examples',
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)


class APIConfig:
    """API-specific configuration"""

    DB_PATH = Config.DB_PATH
    TRACKC_DB_PATH = Config.TRACK_C_DB_PATH
    BASE_DIR = Config.BASE_DIR
    FAISS_DB_PATH = str(PROJECT_ROOT / 'data' / 'knowledge_base' / 'faiss_db' / 'faiss_sar.db')
    OUTPUT_DIR = Config.OUTPUT_DIR
    GENERATED_NARRATIVES_DIR = Config.GENERATED_NARRATIVES_DIR
    AUDIT_LOG_PATH = str(PROJECT_ROOT / 'data' / 'output' / 'audit_logs.jsonl')
    EXPLAIN_LOG_PATH = str(PROJECT_ROOT / 'data' / 'output' / 'explainability_logs.jsonl')

    # JWT Configuration
    SECRET_KEY = "sar-key-2026"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 480

    # Regulatory thresholds (PMLA / RBI / FIU-IND)
    CTR_THRESHOLD = 1_000_000        # Rs 10 lakh - cash transaction reporting
    STR_INCOME_RATIO = 3.0           # 3x monthly income = suspicious
    RAPID_TXN_COUNT = 10             # 10+ txns in short period = rapid movement
    HIGH_RISK_AMOUNT = 5_000_000     # Rs 50 lakh = high value flag
    STRUCTURING_MAX = 950_000        # just below CTR threshold = structuring flag
    MULTI_ACCOUNT_MIN = 5            # 5+ source accounts = layering indicator


ROLES = {
    "ANALYST": [
        "generatesar",
        "viewsar",
        "editsar",
        "approvesar",
        "viewaudit"
    ],
    "COMPLIANCE_OFFICER": [
        "viewsar",
        "viewaudit",
        "exportreports"
    ],
    "ADMIN": ["*"]
}
