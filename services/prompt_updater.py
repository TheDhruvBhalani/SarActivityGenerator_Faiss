"""
Component 4: Prompt Updater
Updates system prompts with learned rules
"""
import sqlite3
import re
import json
from datetime import datetime
from typing import List, Optional

from config.settings import Config
from models.schemas import PromptVersion
from services.pattern_extractor import PatternExtractor


class PromptUpdater:
    """
    Updates system prompts with learned rules
    """

    BASE_PROMPT = """You are an expert Anti-Money Laundering (AML) Compliance Officer with 20 years of experience at a major Indian bank.

CORE PRINCIPLES:
1. TONE: Formal, objective, factual, and legally precise.
2. ACCURACY: Use ONLY facts present in the provided context.
3. STRUCTURE: Follow the standard SAR format with clear sections.
4. CITATIONS: Reference specific regulatory guidelines.
5. COMPLIANCE: Ensure all statements align with PMLA, FIU-IND, and RBI guidelines.

PROHIBITED:
- Do NOT invent facts or transactions
- Do NOT use subjective terms
- Do NOT include personal opinions
- Do NOT deviate from the provided context

You must be boring, accurate, and consistent."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.TRACK_C_DB_PATH
        self.pattern_extractor = PatternExtractor(self.db_path)

    def generate_updated_prompt(self, current_version: str = "v1.0") -> Optional[PromptVersion]:
        """Generate new prompt version with learned rules"""
        active_patterns = self.pattern_extractor.get_active_patterns()

        if not active_patterns:
            return None

        print(f"Generating updated prompt with {len(active_patterns)} learned rules...")

        learned_rules_text = "\n[LEARNED RULES - Auto-Generated from Analyst Feedback]\n"

        pattern_ids = []
        for i, pattern in enumerate(active_patterns, 1):
            learned_rules_text += f"\n{i}. {pattern.pattern_name} (Confidence: {pattern.confidence_score:.0%})\n"
            learned_rules_text += f"   {pattern.rule_instruction}\n"
            pattern_ids.append(pattern.pattern_id)

        updated_prompt = self.BASE_PROMPT + "\n" + learned_rules_text
        new_version = self._increment_version(current_version)

        prompt_version = PromptVersion(
            version=new_version,
            prompt_text=updated_prompt,
            rules_applied=pattern_ids,
            changes_from_previous=f"Added {len(active_patterns)} learned rules",
            previous_version=current_version,
            status="TESTING"
        )

        self._save_to_db(prompt_version)
        print(f"Created prompt version {new_version}")

        return prompt_version

    def _increment_version(self, current: str) -> str:
        """Increment version number"""
        match = re.match(r'v(\d+)\.(\d+)', current)
        if match:
            major, minor = int(match.group(1)), int(match.group(2))
            minor += 1
            if minor >= 10:
                major += 1
                minor = 0
            return f"v{major}.{minor}"
        return "v1.1"

    def get_current_prompt(self) -> str:
        """Retrieve the currently active prompt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT prompt_text FROM prompt_versions
            WHERE status = 'ACTIVE'
            ORDER BY created_date DESC
            LIMIT 1
        ''')

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else self.BASE_PROMPT

    def activate_version(self, version: str):
        """Set a prompt version as ACTIVE"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("UPDATE prompt_versions SET status = 'DEPRECATED' WHERE status = 'ACTIVE'")
        cursor.execute('''
            UPDATE prompt_versions
            SET status = 'ACTIVE', deployment_date = ?
            WHERE version = ?
        ''', (datetime.now().isoformat(), version))

        conn.commit()
        conn.close()

    def _save_to_db(self, prompt_version: PromptVersion):
        """Save prompt version (UPSERT)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO prompt_versions
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', prompt_version.to_db_tuple())

        conn.commit()
        conn.close()

    def get_version_history(self) -> List[PromptVersion]:
        """Get all prompt versions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM prompt_versions ORDER BY created_date DESC')
        rows = cursor.fetchall()
        conn.close()

        versions = []
        for row in rows:
            version = PromptVersion(
                version=row[0],
                prompt_text=row[1],
                rules_applied=json.loads(row[2]),
                changes_from_previous=row[3],
                created_date=row[4],
                created_by=row[5],
                ab_test_results=json.loads(row[6]),
                deployment_date=row[7],
                previous_version=row[8],
                status=row[9],
                notes=row[10]
            )
            versions.append(version)

        return versions
