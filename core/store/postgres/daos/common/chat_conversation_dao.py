from typing import List, Any, Optional, Tuple
from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.chat_conversation import ChatConversation
from ..base_dao import BaseDao


class ChatConversationDao(BaseDao):
    def create(self, conversation_id: str, user_id: str, title: Optional[str]) -> None:
        with self.db.get_session() as session:
            session.execute(
                insert(ChatConversation)
                .values(conversation_id=conversation_id, user_id=user_id, title=title)
                .on_conflict_do_nothing(index_elements=[ChatConversation.conversation_id])
            )

    def get_user_id(self, conversation_id: str) -> Optional[str]:
        with self.db.get_session() as session:
            row = session.query(ChatConversation.user_id).filter(
                ChatConversation.conversation_id == conversation_id
            ).first()
            return row.user_id if row else None

    def update_title(self, conversation_id: str, title: str) -> None:
        with self.db.get_session() as session:
            session.execute(
                update(ChatConversation)
                .where(ChatConversation.conversation_id == conversation_id)
                .values(title=title)
            )

    def get_by_user(self, user_id: str, offset: int, limit: int) -> Tuple[int, List[Any]]:
        with self.db.get_session() as session:
            rows = session.query(
                ChatConversation.conversation_id,
                ChatConversation.title,
                ChatConversation.created_at,
                func.count().over().label("total"),
            ).filter(
                ChatConversation.user_id == user_id
            ).order_by(ChatConversation.created_at.desc()).offset(offset).limit(limit).all()
            total = rows[0].total if rows else 0
            return total, rows
