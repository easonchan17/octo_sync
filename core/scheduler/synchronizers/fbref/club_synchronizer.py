from typing import List, Any
from sqlalchemy import func, and_, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Country, Club, Site, Status, ClubSyncState,
    CountrySyncState, CountrySyncFlag
)
from ..base_synchronizer import BaseSynchronizer

class ClubSynchronizer(BaseSynchronizer):
    def get_clubs(self, site: Site, comp_code: str, club_code: str) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
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
        with self.db.get_session(site.get_namespace()) as session:
            result = session.query(
                ClubSyncState.sync_flags
            ).filter(
                ClubSyncState.code == club_code,
                ClubSyncState.season == season
            ).first()

            if not result:
                return False

            return (result[0] & flag) == flag

    def get_unsynced_countries(self, site: Site) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            return session.query(
                Country.name,
                Country.code
            ).outerjoin(
                CountrySyncState,
                CountrySyncState.code == Country.code
            ).filter(
                Country.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value,
                Country.club_count > 0,
                or_(
                    CountrySyncState.code.is_(None),
                    (CountrySyncState.sync_flags.op('&')(CountrySyncFlag.CLUBS.value)) != CountrySyncFlag.CLUBS.value
                )
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

        with self.db.get_session(site.get_namespace()) as session:
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
                        or_(
                            Club.min_season != insert_stmt.excluded.min_season,
                            and_(
                                Club.min_season.is_(None),
                                insert_stmt.excluded.min_season.isnot(None)
                            ),
                            and_(
                                Club.min_season.isnot(None),
                                insert_stmt.excluded.min_season.is_(None)
                            )
                        ),
                        or_(
                            Club.max_season != insert_stmt.excluded.max_season,
                            and_(
                                Club.max_season.is_(None),
                                insert_stmt.excluded.max_season.isnot(None)
                            ),
                            and_(
                                Club.max_season.isnot(None),
                                insert_stmt.excluded.max_season.is_(None)
                            )
                        )
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} {country.name} clubs completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(CountrySyncState).values(
                code=country.code,
                sync_flags=CountrySyncFlag.CLUBS.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={
                    'sync_flags': CountrySyncState.sync_flags.op('|')(CountrySyncFlag.CLUBS.value),
                    'update_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} {country.name} clubs as synced")