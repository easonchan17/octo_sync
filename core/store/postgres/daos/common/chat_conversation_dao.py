from typing import List, Any, Optional
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.chat_conversation import ChatConversation
from ..base_dao import BaseDao


class ChatConversationDao(BaseDao):
    def create(self, conversation_id: str, user_id: str) -> None:
        with self.db.get_session() as session:
            session.execute(
                insert(ChatConversation)
                .values(conversation_id=conversation_id, user_id=user_id)
                .on_conflict_do_nothing(index_elements=[ChatConversation.conversation_id])
            )

    def get_user_id(self, conversation_id: str) -> Optional[str]:
        with self.db.get_session() as session:
            row = session.query(ChatConversation.user_id).filter(
                ChatConversation.conversation_id == conversation_id
            ).first()
            return row.user_id if row else None

    def get_by_user(self, user_id: str) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                ChatConversation.conversation_id,
                ChatConversation.created_at,
            ).filter(
                ChatConversation.user_id == user_id
            ).order_by(ChatConversation.created_at.desc()).all()
