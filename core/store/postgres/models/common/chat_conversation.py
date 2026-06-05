from sqlalchemy import Column, BigInteger, String, Index
from ..base_model import Base


class ChatConversation(Base):
    __tablename__ = 'chat_conversations'
    __table_args__ = (
        Index('idx_chat_conversations_user_id', 'user_id'),
        Index('idx_chat_conversations_created_at', 'created_at'),
        Index('idx_chat_conversations_updated_at', 'updated_at'),
    )

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, unique=True)
    user_id         = Column(String(64), nullable=False)
    title           = Column(String(100), nullable=True)
