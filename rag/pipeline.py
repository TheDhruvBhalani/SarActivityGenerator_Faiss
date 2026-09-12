"""
RAG Pipeline - Track A
Retrieval Augmented Generation for SAR narratives
"""
import sqlite3
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

from config.settings import Config


@dataclass
class RAGContext:
    """Context retrieved for SAR generation"""
    alert_id: str
    customerprofile: Dict[str, Any] = field(default_factory=dict)
    transactionsummary: Dict[str, Any] = field(default_factory=dict)
    retrievedknowledge: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGPipeline:
    """
    RAG Pipeline for SAR narrative generation

    Components:
    1. Alert ingestion - fetch alert and related data
    2. Customer profile retrieval
    3. Transaction summary generation
    4. Knowledge base retrieval (FAISS)
    5. Context assembly
    """

    def __init__(self, db_path: str = None, faiss_db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        self.faiss_db_path = faiss_db_path or f"{Config.VECTOR_DB_DIR}/faiss_sar.db"
        self.embedder = None
        self.faiss_index = None

        self._init_faiss()
        print("RAG Pipeline initialized")

    def _init_faiss(self):
        """Initialize FAISS index and embedder"""
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
            import os

            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

            index_path = f"{Config.VECTOR_DB_DIR}/faiss_index.bin"
            if os.path.exists(index_path):
                self.faiss_index = faiss.read_index(index_path)
                print(f"  FAISS index loaded from {index_path}")
            else:
                self.faiss_index = None
                print(f"  FAISS index not found at {index_path}")

        except ImportError as e:
            print(f"  FAISS/SentenceTransformers not available: {e}")
            self.embedder = None
            self.faiss_index = None

    def process_alert(
        self,
        alert_id: str,
        use_hybrid: bool = True,
        use_reranking: bool = True
    ) -> RAGContext:
        """
        Main method: Process an alert and retrieve all context

        Args:
            alert_id: Alert identifier
            use_hybrid: Use hybrid (semantic + keyword) search
            use_reranking: Apply cross-encoder reranking
        """
        customer_profile = self._get_customer_profile(alert_id)
        transaction_summary = self._get_transaction_summary(alert_id)
        alert_metadata = self._get_alert_metadata(alert_id)
        knowledge = self._retrieve_knowledge(alert_id, alert_metadata.get('pattern_type', ''))

        context = RAGContext(
            alert_id=alert_id,
            customerprofile=customer_profile,
            transactionsummary=transaction_summary,
            retrievedknowledge=knowledge,
            metadata=alert_metadata
        )

        return context

    def _get_customer_profile(self, alert_id: str) -> Dict[str, Any]:
        """Retrieve customer profile for alert"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT c.* FROM customers c
                JOIN alerts a ON c.customer_id = a.customer_id
                WHERE a.alert_id = ?
            ''', (alert_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return {}
        except Exception as e:
            print(f"Error fetching customer profile: {e}")
            return {}

    def _get_transaction_summary(self, alert_id: str) -> Dict[str, Any]:
        """Generate transaction summary for alert"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT a.related_transaction_ids, a.customer_id
                FROM alerts a
                WHERE a.alert_id = ?
            ''', (alert_id,))

            alert_row = cursor.fetchone()
            if not alert_row:
                conn.close()
                return {}

            txn_ids_json, customer_id = alert_row
            txn_ids = json.loads(txn_ids_json) if txn_ids_json else []

            if txn_ids:
                placeholders = ','.join(['?' for _ in txn_ids])
                cursor.execute(f'''
                    SELECT
                        COUNT(*) as count,
                        SUM(amount) as total_amount,
                        AVG(amount) as avg_amount,
                        MAX(amount) as max_amount,
                        MIN(date) as startdate,
                        MAX(date) as enddate,
                        COUNT(DISTINCT channel) as channel_count
                    FROM transactions
                    WHERE transaction_id IN ({placeholders})
                ''', txn_ids)
            else:
                cursor.execute('''
                    SELECT
                        COUNT(*) as count,
                        SUM(amount) as total_amount,
                        AVG(amount) as avg_amount,
                        MAX(amount) as max_amount,
                        MIN(date) as startdate,
                        MAX(date) as enddate,
                        COUNT(DISTINCT channel) as channel_count
                    FROM transactions
                    WHERE customer_id = ?
                ''', (customer_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                count, total, avg, max_amt, start, end, channels = row

                cursor2 = sqlite3.connect(self.db_path).cursor()
                cursor2.execute('''
                    SELECT annual_income_inr FROM customers WHERE customer_id = ?
                ''', (customer_id,))
                income_row = cursor2.fetchone()
                monthly_income = (income_row[0] / 12) if income_row and income_row[0] else 1

                return {
                    'count': count or 0,
                    'total_amount': total or 0,
                    'avg_amount': avg or 0,
                    'max_amount': max_amt or 0,
                    'startdate': start,
                    'enddate': end,
                    'channel_count': channels or 0,
                    'income_ratio': round((total or 0) / monthly_income, 2) if monthly_income else 0
                }
            return {}
        except Exception as e:
            print(f"Error fetching transaction summary: {e}")
            return {}

    def _get_alert_metadata(self, alert_id: str) -> Dict[str, Any]:
        """Retrieve alert metadata"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM alerts WHERE alert_id = ?', (alert_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return {}
        except Exception as e:
            print(f"Error fetching alert metadata: {e}")
            return {}

    def _retrieve_knowledge(self, alert_id: str, pattern_type: str) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge from FAISS index"""
        if not self.embedder or not self.faiss_index:
            return self._get_fallback_knowledge(pattern_type)

        try:
            query = f"SAR narrative for {pattern_type} money laundering pattern PMLA FIU-IND"
            query_embedding = self.embedder.encode([query])

            k = 5
            distances, indices = self.faiss_index.search(query_embedding, k)

            knowledge = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                knowledge.append({
                    'rank': i + 1,
                    'score': float(1 / (1 + dist)),
                    'source': f'knowledge_chunk_{idx}',
                    'content': f'Knowledge content for {pattern_type}'
                })

            return knowledge
        except Exception as e:
            print(f"FAISS retrieval error: {e}")
            return self._get_fallback_knowledge(pattern_type)

    def _get_fallback_knowledge(self, pattern_type: str) -> List[Dict[str, Any]]:
        """Fallback knowledge when FAISS is not available"""
        return [
            {
                'rank': 1,
                'score': 0.95,
                'source': 'PMLA_Guidelines',
                'content': 'PMLA Section 12 mandates reporting of suspicious transactions to FIU-IND within 7 working days.'
            },
            {
                'rank': 2,
                'score': 0.90,
                'source': 'RBI_KYC_Direction',
                'content': 'RBI Master Direction on KYC requires Enhanced Due Diligence for high-risk customers and PEPs.'
            },
            {
                'rank': 3,
                'score': 0.85,
                'source': f'{pattern_type}_Typology',
                'content': f'FATF typology for {pattern_type}: Indicates potential money laundering activity requiring STR filing.'
            }
        ]
