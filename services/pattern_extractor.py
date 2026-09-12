"""
Component 2: Pattern Extractor
Identifies systematic improvements from multiple feedbacks
"""
import sqlite3
import re
import json
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.settings import Config
from models.schemas import FeedbackEntry, LearnedPattern
from services.feedback_collector import FeedbackCollector


class PatternExtractor:
    """
    Detects systematic patterns from analyst edits

    How it works:
    1. Analyzes multiple feedback entries
    2. Groups similar edits together
    3. Calculates confidence scores
    4. Generates actionable rules for prompt updates
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.TRACK_C_DB_PATH
        self.collector = FeedbackCollector(self.db_path)

    def extract_patterns(
        self,
        min_frequency: int = 3,
        min_confidence: float = 0.6,
        alert_type: Optional[str] = None
    ) -> List[LearnedPattern]:
        """Main method: Extract patterns from feedback history"""
        feedbacks = self.collector.get_all_feedbacks(alert_type)

        if len(feedbacks) < min_frequency:
            print(f"Only {len(feedbacks)} feedbacks available. Need at least {min_frequency}.")
            return []

        print(f"Analyzing {len(feedbacks)} feedback entries...")

        patterns = []
        patterns.extend(self._detect_missing_info_patterns(feedbacks, min_frequency, min_confidence))
        patterns.extend(self._detect_terminology_patterns(feedbacks, min_frequency, min_confidence))
        patterns.extend(self._detect_structure_patterns(feedbacks, min_frequency, min_confidence))
        patterns.extend(self._detect_tone_patterns(feedbacks, min_frequency, min_confidence))

        for pattern in patterns:
            self._save_pattern_to_db(pattern)

        print(f"Detected {len(patterns)} patterns!")
        return patterns

    def _detect_missing_info_patterns(
        self,
        feedbacks: List[FeedbackEntry],
        min_frequency: int,
        min_confidence: float
    ) -> List[LearnedPattern]:
        """Detect patterns where analysts consistently ADD specific information"""
        patterns = []

        info_keywords = {
            "transaction_count": [r'\d+\s+(transactions?|credits?|debits?)', r'\d+\s+NEFT', r'\d+\s+RTGS'],
            "amount": [r'₹[\d,]+\s*(crores?|lakhs?)', r'totaling\s+₹', r'amounting\s+to'],
            "timeframe": [r'\d+\s+days?', r'between\s+\d{4}-\d{2}-\d{2}', r'period\s+of\s+\d+'],
            "channel": [r'NEFT', r'RTGS', r'UPI', r'SWIFT', r'IMPS'],
            "velocity": [r'[\d.]+\s+transactions?/day', r'velocity\s+of', r'frequency\s+of']
        }

        info_additions = defaultdict(list)

        for feedback in feedbacks:
            for info_type, regexes in info_keywords.items():
                for regex in regexes:
                    if re.search(regex, feedback.edited_narrative, re.IGNORECASE):
                        if not re.search(regex, feedback.original_narrative, re.IGNORECASE):
                            info_additions[info_type].append(feedback.feedback_id)
                            break

        for info_type, feedback_ids in info_additions.items():
            frequency = len(feedback_ids)
            total = len(feedbacks)
            confidence = frequency / total

            if frequency >= min_frequency and confidence >= min_confidence:
                pattern = LearnedPattern(
                    pattern_id=f"PTN_MISSING_{info_type.upper()}_{datetime.now().strftime('%Y%m%d')}",
                    pattern_name=f"Missing {info_type.replace('_', ' ').title()}",
                    pattern_type="MISSING_INFO",
                    description=f"Analysts consistently add {info_type.replace('_', ' ')} ({frequency}/{total} cases)",
                    rule_instruction=self._generate_missing_info_rule(info_type),
                    confidence_score=round(confidence, 3),
                    frequency=frequency,
                    total_samples=total,
                    occurrence_rate=round(confidence, 3),
                    alert_types=[feedbacks[0].alert_type] if feedbacks else [],
                    example_feedbacks=feedback_ids[:5],
                    status="ACTIVE" if confidence >= 0.75 else "PENDING"
                )
                patterns.append(pattern)

        return patterns

    def _generate_missing_info_rule(self, info_type: str) -> str:
        """Generate actionable rule instruction for missing info"""
        rules = {
            "transaction_count": "ALWAYS include the exact number of transactions in ACTIVITY SUMMARY.",
            "amount": "ALWAYS include total transaction amounts in Rs crores or lakhs.",
            "timeframe": "ALWAYS specify the exact time period with dates.",
            "channel": "ALWAYS mention the transaction channel (NEFT/RTGS/UPI/SWIFT/IMPS).",
            "velocity": "ALWAYS calculate and mention transaction velocity."
        }
        return rules.get(info_type, f"Include {info_type} information")

    def _detect_terminology_patterns(
        self,
        feedbacks: List[FeedbackEntry],
        min_frequency: int,
        min_confidence: float
    ) -> List[LearnedPattern]:
        """Detect consistent terminology replacements"""
        patterns = []

        terminology_pairs = [
            (r'\bwire transfer', 'NEFT'),
            (r'\bmoney\b', 'funds'),
            (r'\bsuspect\b', 'customer'),
            (r'\bobviously\b', 'appears to indicate'),
            (r'\bclearly\b', 'suggests'),
            (r'\bdefinitely\b', 'likely'),
        ]

        replacements = defaultdict(list)

        for feedback in feedbacks:
            for old_term, new_term in terminology_pairs:
                has_old = bool(re.search(old_term, feedback.original_narrative, re.IGNORECASE))
                has_new = bool(re.search(new_term, feedback.edited_narrative, re.IGNORECASE))

                if has_old and has_new:
                    replacements[f"{old_term}->{new_term}"].append(feedback.feedback_id)

        for replacement, feedback_ids in replacements.items():
            frequency = len(feedback_ids)
            total = len(feedbacks)
            confidence = frequency / total

            if frequency >= min_frequency and confidence >= min_confidence:
                old_term, new_term = replacement.split('->')

                pattern = LearnedPattern(
                    pattern_id=f"PTN_TERM_{old_term.replace(' ', '_').upper()}_{datetime.now().strftime('%Y%m%d')}",
                    pattern_name=f"Terminology: {old_term} -> {new_term}",
                    pattern_type="TERMINOLOGY",
                    description=f"Analysts replace '{old_term}' with '{new_term}' ({frequency}/{total} cases)",
                    rule_instruction=f"Use '{new_term}' instead of '{old_term}'",
                    confidence_score=round(confidence, 3),
                    frequency=frequency,
                    total_samples=total,
                    occurrence_rate=round(confidence, 3),
                    alert_types=[],
                    example_feedbacks=feedback_ids[:5],
                    status="ACTIVE" if confidence >= 0.75 else "PENDING"
                )
                patterns.append(pattern)

        return patterns

    def _detect_structure_patterns(
        self,
        feedbacks: List[FeedbackEntry],
        min_frequency: int,
        min_confidence: float
    ) -> List[LearnedPattern]:
        """Detect structural improvements"""
        patterns = []
        numbered_list_count = 0

        for feedback in feedbacks:
            orig_rationale = self._extract_section_content(feedback.original_narrative, "SUSPICION RATIONALE")
            edit_rationale = self._extract_section_content(feedback.edited_narrative, "SUSPICION RATIONALE")

            if orig_rationale and edit_rationale:
                has_list_orig = bool(re.search(r'^\s*\d+\.', orig_rationale, re.MULTILINE))
                has_list_edit = bool(re.search(r'^\s*\d+\.', edit_rationale, re.MULTILINE))

                if not has_list_orig and has_list_edit:
                    numbered_list_count += 1

        if numbered_list_count >= min_frequency:
            confidence = numbered_list_count / len(feedbacks)

            if confidence >= min_confidence:
                pattern = LearnedPattern(
                    pattern_id=f"PTN_STRUCT_NUMBERED_LIST_{datetime.now().strftime('%Y%m%d')}",
                    pattern_name="Add Numbered List in Rationale",
                    pattern_type="STRUCTURE",
                    description=f"Analysts add numbered lists to SUSPICION RATIONALE ({numbered_list_count}/{len(feedbacks)} cases)",
                    rule_instruction="In SUSPICION RATIONALE, list indicators in numbered format.",
                    confidence_score=round(confidence, 3),
                    frequency=numbered_list_count,
                    total_samples=len(feedbacks),
                    occurrence_rate=round(confidence, 3),
                    alert_types=[],
                    example_feedbacks=[],
                    status="ACTIVE" if confidence >= 0.75 else "PENDING"
                )
                patterns.append(pattern)

        return patterns

    def _detect_tone_patterns(
        self,
        feedbacks: List[FeedbackEntry],
        min_frequency: int,
        min_confidence: float
    ) -> List[LearnedPattern]:
        """Detect tone adjustments (removing definitive language)"""
        patterns = []
        definitive_words = ['clearly', 'obviously', 'definitely', 'certainly', 'undoubtedly']

        removals = 0
        for feedback in feedbacks:
            for word in definitive_words:
                if re.search(rf'\b{word}\b', feedback.original_narrative, re.IGNORECASE):
                    if not re.search(rf'\b{word}\b', feedback.edited_narrative, re.IGNORECASE):
                        removals += 1
                        break

        if removals >= min_frequency:
            confidence = removals / len(feedbacks)

            if confidence >= min_confidence:
                pattern = LearnedPattern(
                    pattern_id=f"PTN_TONE_REMOVE_DEFINITIVE_{datetime.now().strftime('%Y%m%d')}",
                    pattern_name="Remove Definitive Language",
                    pattern_type="TONE",
                    description=f"Analysts remove definitive words ({removals}/{len(feedbacks)} cases)",
                    rule_instruction="AVOID words like 'clearly', 'obviously'. Use 'appears to indicate', 'suggests'.",
                    confidence_score=round(confidence, 3),
                    frequency=removals,
                    total_samples=len(feedbacks),
                    occurrence_rate=round(confidence, 3),
                    alert_types=[],
                    example_feedbacks=[],
                    status="ACTIVE" if confidence >= 0.75 else "PENDING"
                )
                patterns.append(pattern)

        return patterns

    def _extract_section_content(self, narrative: str, section_name: str) -> Optional[str]:
        """Extract content of a specific section"""
        pattern = rf'\[{section_name}\](.*?)(?=\[|$)'
        match = re.search(pattern, narrative, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _save_pattern_to_db(self, pattern: LearnedPattern):
        """Save learned pattern to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT pattern_id FROM learned_patterns WHERE pattern_id = ?', (pattern.pattern_id,))
        exists = cursor.fetchone()

        if exists:
            cursor.execute('''
                UPDATE learned_patterns
                SET confidence_score = ?, frequency = ?, total_samples = ?,
                    occurrence_rate = ?, last_confirmed = ?, status = ?
                WHERE pattern_id = ?
            ''', (pattern.confidence_score, pattern.frequency, pattern.total_samples,
                  pattern.occurrence_rate, pattern.last_confirmed, pattern.status, pattern.pattern_id))
        else:
            cursor.execute('''
                INSERT INTO learned_patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', pattern.to_db_tuple())

        conn.commit()
        conn.close()

    def get_active_patterns(self, alert_type: Optional[str] = None) -> List[LearnedPattern]:
        """Retrieve all ACTIVE patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM learned_patterns
            WHERE status = 'ACTIVE'
            ORDER BY confidence_score DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        patterns = []
        for row in rows:
            pattern = LearnedPattern(
                pattern_id=row[0],
                pattern_name=row[1],
                pattern_type=row[2],
                description=row[3],
                rule_instruction=row[4],
                confidence_score=row[5],
                frequency=row[6],
                total_samples=row[7],
                occurrence_rate=row[8],
                alert_types=json.loads(row[9]),
                example_feedbacks=json.loads(row[10]),
                first_detected=row[11],
                last_confirmed=row[12],
                status=row[13],
                impact_metrics=json.loads(row[14]),
                metadata=json.loads(row[15])
            )
            patterns.append(pattern)

        return patterns
