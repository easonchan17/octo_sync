from abc import ABC
from typing import Any, Dict, List, Type
from core.services.team_resolver import TeamResolver
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.scheduler.tasks.base_task import BaseTask
from sqlalchemy import update

class BaseMapper(BaseTask, ABC):
    def __init__(self) -> None:
        super().__init__()
        self.db = PostgreSQLManager.get_instance()
        self.team_resolver = TeamResolver()

    def _get_unmapped_fixtures(self, raw_model: Type[Any]) -> List[Dict]:
        with self.db.get_session() as session:
            rows = session.query(
                raw_model.id,
                raw_model.kickoff_time,
                raw_model.home_team,
                raw_model.away_team
            ).filter(
                raw_model.fixture_id.is_(None)
            ).order_by(raw_model.kickoff_time).all()

            return [dict(r._mapping) for r in rows]

    def _build_update_mappings(self, raw_matches: List[Dict]) -> List[Dict]:
        update_mappings = []
        for match in raw_matches:
            ref_obj = match.get('ref_obj')
            if ref_obj is None:
                continue

            ref_id = getattr(ref_obj, 'match_id', None)
            if ref_id is None:
                continue

            update_mappings.append({
                'id': match['id'],
                'fixture_id': ref_id
            })
        return update_mappings

    def _update_fixtures(self, raw_model: Type[Any], mappings: List[Dict]) -> None:
        with self.db.get_session() as session:
            session.execute(update(raw_model), mappings)

    def _map_fixtures(self, raw_model: Type[Any], ref_model: Type[Any]) -> None:
        try:
            raw_matches = self._get_unmapped_fixtures(raw_model)

            if not raw_matches:
                self.logger.info(f"No unmapped fixtures found for {raw_model.__name__}")
                return

            self.team_resolver.resolve(
                raw_matches,
                ref_model,
                attach_ref=True
            )

            update_mappings = self._build_update_mappings(raw_matches)

            if not update_mappings:
                self.logger.info(f"No valid matches for {raw_model.__name__}")
                return

            self._update_fixtures(raw_model, update_mappings)
            self.logger.info(f"Successfully mapped {len(update_mappings)} fixtures")
        except Exception as e:
            self.logger.exception(f"Mapping flow failed for {raw_model.__name__}: {e}")
