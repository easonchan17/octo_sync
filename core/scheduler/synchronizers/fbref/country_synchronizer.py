from typing import List
from sqlalchemy import func, update, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Country, Site, Status, GlobalState
)
from ..base_synchronizer import BaseSynchronizer

class CountrySynchronizer(BaseSynchronizer):
    SYNCED_KEY = 'country_synced'
    SYNCED_VALUE = '1'

    def is_synced(self, site: Site) -> bool:
        with self.db.get_session(site.get_namespace()) as session:
            result = session.query(
                GlobalState.value
            ).filter(
                GlobalState.key == self.SYNCED_KEY
            ).first()

            if not result or not result[0]:
                return False

            return result[0] == self.SYNCED_VALUE

    def sync(self, site: Site, countries: List[Country]) -> None:
        if not countries:
            return

        country_dict = self.to_dict(
            countries,
            ['name', 'code', 'player_count', 'club_count'],
            ['code']
        )

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Country).values(list(country_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={
                    'name': insert_stmt.excluded.name,
                    'player_count': insert_stmt.excluded.player_count,
                    'club_count': insert_stmt.excluded.club_count,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        Country.name != insert_stmt.excluded.name,
                        Country.player_count != insert_stmt.excluded.player_count,
                        Country.club_count != insert_stmt.excluded.club_count
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} countries completed. upserted: {upserted_count}")

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
            self.logger.info(f"Mark {site.name} countries as synced")
