from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, ForeignKey
from ..base_model import Base, StatusMixin, DictMixin, Status


class TeamMapping(Base, StatusMixin, DictMixin):
    __tablename__ = 'team_mappings'
    __table_args__ = (
        Index('idx_team_mappings_source_site_source_team', 'source_site', 'source_team', unique=True),
        Index('idx_team_mappings_target_team', 'target_team'),
        Index('idx_team_mappings_target_team_id', 'target_team_id'),
        Index('idx_team_mappings_create_at', 'create_at'),
        Index('idx_team_mappings_update_at', 'update_at'),
        {'schema': 'public'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_site = Column(Integer, nullable=False)
    source_team = Column(String(100), nullable=False)

    target_team = Column(String(100), nullable=False)
    target_team_id = Column(Integer, nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<TeamMapping({self.source_site}: {self.source_team} -> {self.target_team})>"
