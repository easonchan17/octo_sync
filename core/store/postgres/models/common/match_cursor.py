from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, Index, CHAR
from ..base_model import Base, StatusMixin, DictMixin, Status

class MatchCursor(Base, StatusMixin, DictMixin):
    __tablename__ = 'match_cursors'
    __table_args__ = (
        Index('idx_match_cursors_created_at', 'created_at'),
        Index('idx_match_cursors_updated_at', 'updated_at'),
        Index('idx_match_cursors_comp_code_team_code', 'comp_code', 'team_code', unique=True),
        {'schema': 'public'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    comp_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)
    last_kickoff_time = Column(DateTime(timezone=True), nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
