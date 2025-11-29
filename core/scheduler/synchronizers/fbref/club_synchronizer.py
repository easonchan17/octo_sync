from typing import List, Any
from sqlalchemy import func, update, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Country, Club, Site, Status, ClubStatus
)
from ..base_synchronizer import BaseSynchronizer

class ClubSynchronizer(BaseSynchronizer):
    def get_clubs(self, site: Site, comp_code: str, club_code: str) -> List[Any]:
        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            if club_code:
                return session.query(
                    Club.name,
                    Club.code
                ).filter(
                    Club.code == club_code
                ).all()

            if comp_code:
                return session.query(
                    Club.name,
                    Club.code
                ).filter(
                    Club.comp_code == comp_code
                ).all()

            return []

    def is_synced(self, site: Site, club_code: str, season: int, flag: int) -> bool:
        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            result = session.query(
                ClubStatus.sync_flags
            ).filter(
                ClubStatus.code == club_code,
                ClubStatus.season == season
            ).first()

            if not result:
                return False

            return (result[0] & flag) == flag

    def get_unsynced_countries(self, site: Site) -> List[Any]:
        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            return session.query(
                Country.name,
                Country.code
            ).filter(
                Country.status.op('&')(Status.SYNCED.value) == 0,
                Country.club_count > 0
            ).all()

    def sync(self, site: Site, country: Country, clubs: List[Club]) -> None:
        if not clubs:
            self.logger.warning(f"No clubs to sync for {site.name} {country.name}")
            return

        club_dict = self.to_dict(
            clubs,
            ['name', 'code', 'gender', 'country_name', 'country_code',
                'comp_name', 'comp_code', 'min_season', 'max_season'],
            ['code']
        )

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Club).values(list(club_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={
                    'name': insert_stmt.excluded.name,
                    'country_name': insert_stmt.excluded.country_name,
                    'country_code': insert_stmt.excluded.country_code,
                    'comp_name': insert_stmt.excluded.comp_name,
                    'comp_code': insert_stmt.excluded.comp_code,
                    'min_season': insert_stmt.excluded.min_season,
                    'max_season': insert_stmt.excluded.max_season,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        Club.name != insert_stmt.excluded.name,
                        Club.country_name != insert_stmt.excluded.country_name,
                        Club.country_code != insert_stmt.excluded.country_code,
                        Club.comp_name != insert_stmt.excluded.comp_name,
                        Club.comp_code != insert_stmt.excluded.comp_code,
                        Club.min_season != insert_stmt.excluded.min_season,
                        Club.max_season != insert_stmt.excluded.max_season
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} {country.name} clubs completed. upserted: {upserted_count}")

            update_stmt = (
                update(Country)
                .where(
                    Country.code == country.code
                )
                .values(
                    status=Country.status.op('|')(Status.SYNCED.value)
                )
            )
            session.execute(update_stmt)
            self.logger.info(f"Mark {site.name} {country.name} clubs as synced")