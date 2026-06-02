from sqlalchemy import Column, BigInteger, String, Text, Index, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from ..base_model import Base


class FeedbackIssue(Base):
    __tablename__ = 'feedback_issues'
    __table_args__ = (
        Index('idx_feedback_issues_conversation_id', 'conversation_id'),
        Index('idx_feedback_issues_user_id', 'user_id'),
        Index('idx_feedback_issues_category', 'category'),
        Index('idx_feedback_issues_severity', 'severity'),
        Index('idx_feedback_issues_created_at', 'created_at'),
        Index('idx_feedback_issues_updated_at', 'updated_at'),
    )

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False)
    user_id         = Column(String(64), nullable=False)
    title           = Column(String(200), nullable=False)
    description     = Column(Text, nullable=False)
    category        = Column(String(50), nullable=False)
    severity        = Column(String(20), nullable=False)
    match_code      = Column(String(16), nullable=True)
    raw_context     = Column(JSONB, nullable=True)
    resolved_at     = Column(DateTime(timezone=True), nullable=True)
