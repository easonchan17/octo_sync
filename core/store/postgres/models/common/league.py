from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, String, Integer, Index, ForeignKeyConstraint, UniqueConstraint, BigInteger
from core.types.enums import LeaguePriority
from ..base_model import Base


class CanonicalLeague(Base):
    __tablename__ = 'canonical_leagues'
    __table_args__ = (
        Index('idx_canonical_leagues_created_at', 'created_at'),
        Index('idx_canonical_leagues_updated_at', 'updated_at'),
        Index('idx_canonical_leagues_priority', 'priority')
    )

    id = Column(BigInteger, primary_key=True)
    country_code = Column(String(3), nullable=True)
    country_name = Column(String(100), nullable=True)

    name = Column(String(200), nullable=False, info={'repr': True})
    priority = Column(Integer, default=LeaguePriority.LEVEL_BASIC.value, info={'repr': True})

    site_leagues = relationship("SiteLeague", back_populates="ref_league", lazy="selectin")


class SiteLeague(Base):
    __tablename__ = 'site_leagues'
    __table_args__ = (
        Index('idx_site_leagues_created_at', 'created_at'),
        Index('idx_site_leagues_updated_at', 'updated_at'),
        UniqueConstraint('site_name', 'league_id', name='uq_site_league_site_code'),
        UniqueConstraint('ref_league_id', 'site_name', name='uq_site_league_league_id_site'),
        ForeignKeyConstraint(['ref_league_id'], ['canonical_leagues.id'], name='site_leagues_ref_league_id_fkey')
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_name = Column(String(100), nullable=False, info={'repr': True})

    country_code = Column(String(3), nullable=True)
    country_name = Column(String(100), nullable=True)

    league_id = Column(String(100), nullable=False, info={'repr': True})
    league_name = Column(String(200), nullable=False)

    extra_data = Column(JSONB(none_as_null=True), nullable=True)

    ref_league_id = Column(BigInteger, nullable=True)
    ref_league = relationship("CanonicalLeague", back_populates="site_leagues", foreign_keys=[ref_league_id])