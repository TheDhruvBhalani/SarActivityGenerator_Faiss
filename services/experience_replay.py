"""
Component 3: Experience Replay
Stores and retrieves high-quality SARs as examples
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.settings import Config
from models.schemas import ExperienceEntry


class ExperienceReplay:
    """
    Manages library of successful SARs

    How it works:
    1. Identifies high-quality approved SARs (low edits, high score)
    2. Stores them with key features for similarity matching
    3. Retrieves most relevant past SAR for new alerts
    4. Injects as dynamic few-shot example
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.TRACK_C_DB_PATH

    def add_experience(
        self,
        alert_id: str,
        alert_type: str,
        approved_narrative: str,
        rag_context: Dict[str, Any],
        edit_count: int,
        analyst_id: str
    ) -> Optional[ExperienceEntry]:
        """Add a successful SAR to the experience library"""
        quality_score = self._calculate_quality(edit_count)

        if quality_score < 70:
            print(f"Quality score {quality_score} too low. Not adding to library.")
            return None

        customer_summary = self._extract_customer_summary(rag_context)
        transaction_summary = self._extract_transaction_summary(rag_context)
        key_features = self._extract_key_features(rag_context)

        experience = ExperienceEntry(
            experience_id=f"EXP_{alert_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            alert_id=alert_id,
            alert_type=alert_type,
            quality_score=quality_score,
            edit_count=edit_count,
            approved_narrative=approved_narrative,
            rag_context=rag_context,
            customer_profile_summary=customer_summary,
            transaction_pattern_summary=transaction_summary,
            key_features=key_features,
            analyst_id=analyst_id
        )

        self._save_to_db(experience)
        print(f"Added {experience.experience_id} to library (quality: {quality_score})")
        return experience

    def _calculate_quality(self, edit_count: int) -> float:
        """Calculate quality score based on edit count"""
        return max(0, 100 - (edit_count * 5))

    def _extract_customer_summary(self, rag_context: Dict[str, Any]) -> str:
        """Extract customer profile summary for matching"""
        customer = rag_context.get('customer_profile', {})
        return f"{customer.get('occupation', 'Unknown')} | Income: Rs{customer.get('annual_income_inr', 0)} | Risk: {customer.get('risk_rating', 'Unknown')}"

    def _extract_transaction_summary(self, rag_context: Dict[str, Any]) -> str:
        """Extract transaction pattern summary for matching"""
        txn = rag_context.get('transaction_summary', {})
        return f"Count: {txn.get('total_transactions', 0)} | Amount: Rs{txn.get('total_amount', 0)} | Velocity: {txn.get('velocity_per_day', 0)}"

    def _extract_key_features(self, rag_context: Dict[str, Any]) -> Dict[str, float]:
        """Extract numeric features for similarity calculation"""
        customer = rag_context.get('customer_profile', {})
        txn = rag_context.get('transaction_summary', {})

        return {
            'transaction_count': float(txn.get('total_transactions', 0)),
            'total_amount': float(txn.get('total_amount', 0)),
            'velocity': float(txn.get('velocity_per_day', 0)),
            'annual_income': float(customer.get('annual_income_inr', 0)),
        }

    def find_similar_experience(
        self,
        alert_type: str,
        rag_context: Dict[str, Any],
        top_k: int = 1
    ) -> List[ExperienceEntry]:
        """Find most similar past SAR from experience library"""
        experiences = self._get_experiences_by_type(alert_type)

        if not experiences:
            print(f"No experiences found for alert type: {alert_type}")
            return []

        current_features = self._extract_key_features(rag_context)

        similarities = []
        for exp in experiences:
            similarity = self._calculate_similarity(current_features, exp.key_features)
            similarities.append((exp, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        top_experiences = [exp for exp, score in similarities[:top_k]]

        if top_experiences:
            print(f"Found {len(top_experiences)} similar experience(s)")

        return top_experiences

    def _calculate_similarity(self, features1: Dict[str, float], features2: Dict[str, float]) -> float:
        """Calculate similarity between two feature sets"""
        def normalize(value, min_val, max_val):
            if max_val == min_val:
                return 0.5
            return (value - min_val) / (max_val - min_val)

        distances = []
        for key in features1.keys():
            if key in features2:
                val1 = features1[key]
                val2 = features2[key]
                max_val = max(val1, val2, 1)
                min_val = 0

                norm1 = normalize(val1, min_val, max_val)
                norm2 = normalize(val2, min_val, max_val)

                distance = abs(norm1 - norm2)
                distances.append(distance)

        avg_distance = sum(distances) / len(distances) if distances else 1.0
        similarity = 1 - avg_distance

        return similarity

    def _get_experiences_by_type(self, alert_type: str) -> List[ExperienceEntry]:
        """Retrieve experiences filtered by alert type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM experience_library
            WHERE alert_type = ?
            ORDER BY quality_score DESC
        ''', (alert_type,))

        rows = cursor.fetchall()
        conn.close()

        experiences = []
        for row in rows:
            exp = ExperienceEntry(
                experience_id=row[0],
                alert_id=row[1],
                alert_type=row[2],
                quality_score=row[3],
                edit_count=row[4],
                approved_narrative=row[5],
                rag_context=json.loads(row[6]),
                customer_profile_summary=row[7],
                transaction_pattern_summary=row[8],
                key_features=json.loads(row[9]),
                analyst_id=row[10],
                approval_date=row[11],
                usage_count=row[12],
                last_used=row[13],
                metadata=json.loads(row[14])
            )
            experiences.append(exp)

        return experiences

    def _save_to_db(self, experience: ExperienceEntry):
        """Save experience to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO experience_library VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', experience.to_db_tuple())

        conn.commit()
        conn.close()

    def update_usage(self, experience_id: str):
        """Increment usage count when experience is used as example"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE experience_library
            SET usage_count = usage_count + 1, last_used = ?
            WHERE experience_id = ?
        ''', (datetime.now().isoformat(), experience_id))

        conn.commit()
        conn.close()
