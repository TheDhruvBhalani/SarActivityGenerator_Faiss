"""
Database schema definitions and initialization
"""
import sqlite3
from config.settings import Config


def initialize_main_database(db_path: str = None):
    """
    Initialize the main SAR database with customers, transactions, and alerts tables
    """
    path = db_path or Config.DB_PATH
    conn = sqlite3.connect(path)

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id VARCHAR(10) PRIMARY KEY,
        name VARCHAR(100),
        date_of_birth DATE,
        age INTEGER,
        gender VARCHAR(10),
        occupation VARCHAR(50),
        annual_income_inr BIGINT,
        risk_rating VARCHAR(10),
        account_type VARCHAR(20),
        account_open_date DATE,
        pan_number VARCHAR(10),
        aadhaar_number VARCHAR(12),
        mobile_number VARCHAR(13),
        email VARCHAR(100),
        address TEXT,
        city VARCHAR(50),
        pep_flag VARCHAR(3),
        kyc_status VARCHAR(20)
    );

    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id VARCHAR(10) PRIMARY KEY,
        account_number VARCHAR(14),
        customer_id VARCHAR(10),
        date TIMESTAMP,
        type VARCHAR(10),
        amount DECIMAL(15,2),
        currency VARCHAR(3),
        counterparty VARCHAR(20),
        channel VARCHAR(10),
        description TEXT,
        suspicious_flag VARCHAR(3),
        pattern_type VARCHAR(20)
    );

    CREATE TABLE IF NOT EXISTS alerts (
        alert_id VARCHAR(10) PRIMARY KEY,
        customer_id VARCHAR(10),
        pattern_type VARCHAR(20),
        description TEXT,
        alert_risk_score INTEGER,
        related_transaction_ids TEXT,
        priority VARCHAR(10),
        assigned_analyst VARCHAR(50),
        status VARCHAR(20) DEFAULT 'Open'
    );

    CREATE INDEX IF NOT EXISTS idx_customer_date ON transactions(customer_id, date);
    CREATE INDEX IF NOT EXISTS idx_suspicious ON transactions(suspicious_flag, pattern_type);
    CREATE INDEX IF NOT EXISTS idx_alert_pattern ON alerts(pattern_type);
    """)

    conn.commit()
    conn.close()
    print(f"Main database initialized at: {path}")


def initialize_track_c_database(db_path: str = None):
    """
    Creates 5 tables for Track C's continual learning system:
    1. feedback_entries - what analysts changed
    2. learned_patterns - systematic improvements discovered
    3. experience_library - successful SARs to reuse
    4. prompt_versions - how the system evolved
    5. learning_metrics - proof of improvement
    """
    path = db_path or Config.TRACK_C_DB_PATH
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    print("Creating Track C database tables...")

    # TABLE 1: FEEDBACK_ENTRIES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback_entries (
            feedback_id TEXT PRIMARY KEY,
            alert_id TEXT NOT NULL,
            alert_type TEXT,
            generation_id TEXT,
            original_narrative TEXT NOT NULL,
            edited_narrative TEXT NOT NULL,
            diff_added TEXT,
            diff_removed TEXT,
            diff_changed TEXT,
            edit_count INTEGER,
            edit_distance INTEGER,
            section_edits TEXT,
            analyst_id TEXT,
            timestamp TEXT,
            approval_status TEXT,
            quality_score REAL,
            metadata TEXT
        )
    ''')

    # TABLE 2: LEARNED_PATTERNS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learned_patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_name TEXT NOT NULL,
            pattern_type TEXT,
            description TEXT,
            rule_instruction TEXT,
            confidence_score REAL,
            frequency INTEGER,
            total_samples INTEGER,
            occurrence_rate REAL,
            alert_types TEXT,
            example_feedbacks TEXT,
            first_detected TEXT,
            last_confirmed TEXT,
            status TEXT,
            impact_metrics TEXT,
            metadata TEXT
        )
    ''')

    # TABLE 3: EXPERIENCE_LIBRARY
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experience_library (
            experience_id TEXT PRIMARY KEY,
            alert_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            quality_score REAL,
            edit_count INTEGER,
            approved_narrative TEXT NOT NULL,
            rag_context TEXT,
            customer_profile_summary TEXT,
            transaction_pattern_summary TEXT,
            key_features TEXT,
            analyst_id TEXT,
            approval_date TEXT,
            usage_count INTEGER DEFAULT 0,
            last_used TEXT,
            metadata TEXT
        )
    ''')

    # TABLE 4: PROMPT_VERSIONS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompt_versions (
            version TEXT PRIMARY KEY,
            prompt_text TEXT NOT NULL,
            rules_applied TEXT,
            changes_from_previous TEXT,
            created_date TEXT,
            created_by TEXT,
            ab_test_results TEXT,
            deployment_date TEXT,
            previous_version TEXT,
            status TEXT,
            notes TEXT
        )
    ''')

    # TABLE 5: LEARNING_METRICS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_metrics (
            metric_id TEXT PRIMARY KEY,
            metric_type TEXT,
            metric_value REAL,
            sar_count INTEGER,
            window_start TEXT,
            window_end TEXT,
            prompt_version TEXT,
            alert_type TEXT,
            timestamp TEXT,
            metadata TEXT
        )
    ''')

    # Create indexes
    print("Creating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_alert ON feedback_entries(alert_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback_entries(alert_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback_entries(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_status ON learned_patterns(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_confidence ON learned_patterns(confidence_score)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_experience_type ON experience_library(alert_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_experience_quality ON experience_library(quality_score)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_type ON learning_metrics(metric_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON learning_metrics(timestamp)')

    conn.commit()
    conn.close()

    print(f"Track C database initialized at: {path}")
    print("  - 5 tables created")
    print("  - 9 indexes created")
