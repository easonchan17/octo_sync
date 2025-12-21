from datetime import datetime
from sqlalchemy import func, or_
from typing import List, Any, Optional
from core.store.postgres.models import Site
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.team_mapping import TeamMapping
from core.store.postgres.models.pinnacle.match import Match as PinnacleMatch
from core.store.postgres.models.fotmob.fixture import Fixture as FotMobFixture
from ..base_synchronizer import BaseSynchronizer

MODEL_REGISTRY = {
    'pinnacle': PinnacleMatch,
    'fotmob': FotMobFixture,
}

class TeamMappingSynchronizer(BaseSynchronizer):
    def get_site(self, site_name: str) -> Optional[Site]:
        if not site_name:
            raise ValueError(f"Site name is required")

        with self.db.get_session() as session:
            site = session.query(Site).filter(Site.name == site_name).first()
            if site:
                session.expunge(site)
            return site

    def get_matches(self, site: Site, league_id: int, start_time: datetime) -> Optional[List[Any]]:
        if not site:
            raise ValueError(f"Site is required")

        model = MODEL_REGISTRY.get(site.name)
        if not model:
            raise ValueError(f"Model not found for site: {site.name}")

        with self.db.get_session(site.get_namespace()) as session:
            matches = session.query(model).filter(
                model.league_id == league_id,
                model.kickoff_time >= start_time
            ).all()
            if matches:
                session.expunge_all()
            return matches

    def sync(self, records: List[Any]) -> None:
        if not records:
            self.logger.warning("No team mappings to sync")
            return

        with self.db.get_session() as session:
            insert_stmt = insert(TeamMapping).values(records)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['source_site', 'source_team'],
                set_={
                    'target_team': insert_stmt.excluded.target_team,
                    'target_team_id': insert_stmt.excluded.target_team_id,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        TeamMapping.target_team != insert_stmt.excluded.target_team,
                        TeamMapping.target_team_id != insert_stmt.excluded.target_team_id
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync team mappings completed. upserted: {upserted_count}")