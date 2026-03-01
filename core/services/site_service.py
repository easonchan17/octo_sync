from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert
from core.utils.singleton import Singleton
from core.services.base_service import BaseService
from core.store.postgres.models import (
    Site, TrainingRecord, SysVal, FotmobFixture, MatchLineup, PinnacleFixture, Moneyline, Spread, CompTeam, CompSyncState,
    MatchStatsSyncState, MatchResult, FbrefFixture, GoalAndShotCreation, Passing,
    DefensiveAction, Shooting, GoalKeeping, PlayerMatchStats,
    PlayerStatsSyncState, MarketOdds, EloRating
)

class SiteService(BaseService, Singleton):
    SITE_TABLES = {
        "public": [Site, TrainingRecord, SysVal],
        "fotmob": [FotmobFixture, MatchLineup],
        "pinnacle": [PinnacleFixture, Moneyline, Spread],
        "fbref": [
            CompTeam, CompSyncState, MatchStatsSyncState,
            MatchResult, FbrefFixture, GoalAndShotCreation, Passing, DefensiveAction,
            Shooting, GoalKeeping, PlayerMatchStats, PlayerStatsSyncState, MarketOdds,
            EloRating
        ],
    }

    def __init__(self) -> None:
        super().__init__()

    def create_site(self, site_name: str, url: str) -> Site:
        self.db.create_tables(self.SITE_TABLES.get("public"))

        with self.db.get_session() as session:
            stmt = (
                insert(Site)
                .values(name=site_name, url=url)
                .on_conflict_do_update(
                    index_elements=['name'],
                    set_={'url': url, 'updated_at': func.now()}
                )
                .returning(Site)
            )
            site = session.execute(stmt).scalar_one()
            session.expunge(site)

        namespace = site.get_namespace()
        self.db.create_schema(namespace)
        self.db.create_tables(self.SITE_TABLES.get(site_name))

        return site
