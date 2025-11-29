from typing import List
from sqlalchemy import func, update, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Competition, Site, GlobalState
)
from ..base_synchronizer import BaseSynchronizer

class CompetitionSynchronizer(BaseSynchronizer):
    SYNCED_KEY = 'competition_synced'
    SYNCED_VALUE = '1'

    def is_synced(self, site: Site) -> bool:
        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            result = session.query(
                GlobalState.value
            ).filter(
                GlobalState.key == self.SYNCED_KEY
            ).first()

            if not result or not result[0]:
                return False

            return result[0] == self.SYNCED_VALUE

    def sync(self, site: Site, competitions: List[Competition]) -> None:
        if not competitions:
            return

        competition_dict = self.to_dict(
            competitions,
            ['name', 'code', 'gender', 'governing_body', 'min_season', 'max_season'],
            ['code']
        )

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Competition).values(list(competition_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={
                    'name': insert_stmt.excluded.name,
                    'governing_body': insert_stmt.excluded.governing_body,
                    'min_season': insert_stmt.excluded.min_season,
                    'max_season': insert_stmt.excluded.max_season,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        Competition.name != insert_stmt.excluded.name,
                        Competition.governing_body != insert_stmt.excluded.governing_body,
                        Competition.min_season != insert_stmt.excluded.min_season,
                        Competition.max_season != insert_stmt.excluded.max_season
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} competitions completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(GlobalState).values(
                key=self.SYNCED_KEY,
                value=self.SYNCED_VALUE
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['key'],
                set_={
                    'value': self.SYNCED_VALUE,
                    'update_at': func.now()
                },
                where=(
                    GlobalState.value != self.SYNCED_VALUE
                )
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} competitions as synced")