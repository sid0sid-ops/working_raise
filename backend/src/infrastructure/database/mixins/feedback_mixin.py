"""
Postgres Feedback Store Mixin
=============================
Handles saving and aggregating user rating feedback on answer quality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger("raise.infrastructure.database.postgres.feedback")


class FeedbackStoreMixin:
    """Provides methods for managing user feedback in PostgreSQL."""

    def save_feedback(
        self,
        session_id: str,
        rating: str,
        reason: Optional[str] = None,
        query: Optional[str] = None,
        message_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> bool:
        """
        Record user feedback on answer quality.
        """
        record = {
            "session_id": session_id,
            "rating": str(rating),
            "reason": reason or "",
            "query": query or "",
            "message_id": message_id or "",
            "client_ip": client_ip or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._memory_feedback.append(record)

        if not self.is_connected:
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chat_feedback (session_id, query, rating, reason, message_id, client_ip)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, query, str(rating), reason, message_id, client_ip))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save feedback in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Returns aggregated thumbs_up, thumbs_down, satisfaction ratio, and total feedback count.
        """
        if not self.is_connected:
            t_up = sum(1 for f in self._memory_feedback if f.get("rating") in ("thumbs_up", "positive"))
            t_down = sum(1 for f in self._memory_feedback if f.get("rating") in ("thumbs_down", "negative"))
            total = len(self._memory_feedback)
            ratio = round(t_up / total, 3) if total > 0 else 1.0
            return {
                "thumbs_up": t_up,
                "thumbs_down": t_down,
                "satisfaction_ratio": ratio,
                "total_feedback": total,
            }

        conn = self._get_connection()
        if not conn:
            raise RuntimeError("Database connection unavailable")
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT rating, COUNT(id)
                FROM chat_feedback
                GROUP BY rating
            """)
            counts = dict(cur.fetchall())
            cur.close()
            t_up = counts.get("thumbs_up", 0) + counts.get("positive", 0)
            t_down = counts.get("thumbs_down", 0) + counts.get("negative", 0)
            total = t_up + t_down
            ratio = round(t_up / total, 3) if total > 0 else 1.0
            return {
                "thumbs_up": t_up,
                "thumbs_down": t_down,
                "satisfaction_ratio": ratio,
                "total_feedback": total,
            }
        except Exception as e:
            logger.error(f"Failed to fetch feedback stats from PostgreSQL: {e}")
            raise
        finally:
            self._release_connection(conn)
