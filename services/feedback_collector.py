"""
Component 1: Feedback Collector
Captures and analyzes analyst edits
"""
import sqlite3
import difflib
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from config.settings import Config
from models.schemas import FeedbackEntry


class FeedbackCollector:
    """
    Captures analyst edits and performs diff analysis

    How it works:
    1. Takes original AI narrative + analyst edited version
    2. Performs diff analysis (what was added/removed/changed)
    3. Calculates edit distance and quality score
    4. Stores in database for pattern detection
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.TRACK_C_DB_PATH

    def collect_feedback(
        self,
        alert_id: str,
        alert_type: str,
        generation_id: str,
        original_narrative: str,
        edited_narrative: str,
        analyst_id: str = "ANALYST_001",
        approval_status: str = "APPROVED"
    ) -> FeedbackEntry:
        """
        Main method: Collect and analyze analyst feedback
        """
        feedback_id = f"FEED_{alert_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        diff_added, diff_removed, diff_changed = self._compute_diff(
            original_narrative,
            edited_narrative
        )

        edit_count = len(diff_added) + len(diff_removed) + len(diff_changed)
        edit_distance = self._compute_edit_distance(original_narrative, edited_narrative)
        section_edits = self._analyze_section_edits(original_narrative, edited_narrative)
        quality_score = self._calculate_quality_score(edit_count, edit_distance, len(original_narrative))

        feedback = FeedbackEntry(
            feedback_id=feedback_id,
            alert_id=alert_id,
            alert_type=alert_type,
            generation_id=generation_id,
            original_narrative=original_narrative,
            edited_narrative=edited_narrative,
            diff_added=diff_added,
            diff_removed=diff_removed,
            diff_changed=diff_changed,
            edit_count=edit_count,
            edit_distance=edit_distance,
            section_edits=section_edits,
            analyst_id=analyst_id,
            approval_status=approval_status,
            quality_score=quality_score,
            metadata={
                "original_length": len(original_narrative),
                "edited_length": len(edited_narrative),
                "length_change": len(edited_narrative) - len(original_narrative)
            }
        )

        self._save_to_database(feedback)
        return feedback

    def _compute_diff(
        self,
        original: str,
        edited: str
    ) -> Tuple[List[str], List[str], List[Dict[str, str]]]:
        """Compute what was added, removed, and changed"""
        original_lines = original.split('\n')
        edited_lines = edited.split('\n')

        diff = list(difflib.unified_diff(original_lines, edited_lines, lineterm=''))

        added = []
        removed = []
        changed = []

        for line in diff:
            if line.startswith('+ '):
                added.append(line[2:])
            elif line.startswith('- '):
                removed.append(line[2:])

        for rem in removed[:]:
            for add in added[:]:
                if self._are_similar(rem, add):
                    changed.append({"from": rem, "to": add})
                    removed.remove(rem)
                    added.remove(add)
                    break

        return added, removed, changed

    def _are_similar(self, str1: str, str2: str, threshold: float = 0.6) -> bool:
        """Check if two strings are similar (likely a modification)"""
        similarity = difflib.SequenceMatcher(None, str1, str2).ratio()
        return similarity > threshold

    def _compute_edit_distance(self, original: str, edited: str) -> int:
        """Compute Levenshtein edit distance"""
        m, n = len(original), len(edited)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if original[i-1] == edited[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])

        return dp[m][n]

    def _analyze_section_edits(self, original: str, edited: str) -> Dict[str, Any]:
        """Analyze which sections had the most edits"""
        sections = [
            "INTRODUCTION",
            "ACTIVITY SUMMARY",
            "SUSPICION RATIONALE",
            "REGULATORY REFERENCES",
            "CONCLUSION"
        ]

        section_edits = {}

        for section in sections:
            orig_section = self._extract_section(original, section)
            edit_section = self._extract_section(edited, section)

            if orig_section and edit_section:
                section_distance = self._compute_edit_distance(orig_section, edit_section)
                section_edits[section] = {
                    "edit_distance": section_distance,
                    "was_modified": section_distance > 0
                }

        return section_edits

    def _extract_section(self, narrative: str, section_name: str) -> Optional[str]:
        """Extract content of a specific section"""
        pattern = rf'\[{section_name}\](.*?)(?=\[|$)'
        match = re.search(pattern, narrative, re.DOTALL)
        return match.group(1).strip() if match else None

    def _calculate_quality_score(self, edit_count: int, edit_distance: int, original_length: int) -> float:
        """Calculate quality score (0-100)"""
        edit_penalty = min(50, edit_count * 2.5)
        distance_ratio = edit_distance / max(original_length, 1)
        distance_penalty = min(50, distance_ratio * 100)
        score = max(0, 100 - edit_penalty - distance_penalty)
        return round(score, 2)

    def _save_to_database(self, feedback: FeedbackEntry):
        """Save feedback entry to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO feedback_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', feedback.to_db_tuple())

        conn.commit()
        conn.close()

    def get_all_feedbacks(self, alert_type: Optional[str] = None) -> List[FeedbackEntry]:
        """Retrieve all feedback entries (optionally filtered by alert type)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if alert_type:
            cursor.execute('''
                SELECT * FROM feedback_entries WHERE alert_type = ?
                ORDER BY timestamp DESC
            ''', (alert_type,))
        else:
            cursor.execute('''
                SELECT * FROM feedback_entries
                ORDER BY timestamp DESC
            ''')

        rows = cursor.fetchall()
        conn.close()

        feedbacks = []
        for row in rows:
            feedback = FeedbackEntry(
                feedback_id=row[0],
                alert_id=row[1],
                alert_type=row[2],
                generation_id=row[3],
                original_narrative=row[4],
                edited_narrative=row[5],
                diff_added=json.loads(row[6]),
                diff_removed=json.loads(row[7]),
                diff_changed=json.loads(row[8]),
                edit_count=row[9],
                edit_distance=row[10],
                section_edits=json.loads(row[11]),
                analyst_id=row[12],
                timestamp=row[13],
                approval_status=row[14],
                quality_score=row[15],
                metadata=json.loads(row[16])
            )
            feedbacks.append(feedback)

        return feedbacks
