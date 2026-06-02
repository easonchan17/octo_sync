from typing import Optional, List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.feedback_issue import FeedbackIssue
from ..base_dao import BaseDao


class FeedbackIssueDao(BaseDao):
    def create(self, conversation_id: str, user_id: str, data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            session.execute(insert(FeedbackIssue).values(
                conversation_id=conversation_id,
                user_id=user_id,
                title=data['title'],
                description=data['description'],
                category=data['category'],
                severity=data['severity'],
                match_code=data.get('match_code'),
                raw_context=data.get('raw_context'),
            ))

    def search_recent(self, keyword: str, limit: int = 3) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(FeedbackIssue).filter(
                FeedbackIssue.description.ilike(f'%{keyword[:50]}%')
            ).order_by(
                FeedbackIssue.created_at.desc()
            ).limit(limit).all()
