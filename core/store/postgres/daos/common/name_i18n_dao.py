from typing import List, Any, Dict, Optional
from sqlalchemy import case
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.name_i18n import NameI18n, NameI18nScanProgress
from core.store.postgres.models.common.league import SiteLeague
from core.store.postgres.models.fotmob.fixture import Fixture
from core.types.enums import SiteName
from ..base_dao import BaseDao


class NameI18nDao(BaseDao):
    BATCH_SIZE = 500

    def get_fotmob_pending_fetch_teams(self, last_id: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.id,
                Fixture.home_code,
                Fixture.home_team,
                Fixture.away_code,
                Fixture.away_team,
            ).filter(
                Fixture.id > last_id,
                Fixture.season > 0,
            ).order_by(Fixture.id.asc()).limit(self.BATCH_SIZE).all()

    def get_pending_fetch_leagues(self, last_id: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                SiteLeague.id,
                SiteLeague.ref_league_id,
                SiteLeague.league_name,
            ).filter(
                SiteLeague.site_name == SiteName.FOTMOB.value,
                SiteLeague.ref_league_id.isnot(None),
                SiteLeague.id > last_id,
            ).order_by(SiteLeague.id.asc()).all()

    def get_scan_progress(self, entity_type: str) -> int:
        with self.db.get_session() as session:
            row = session.query(NameI18nScanProgress.last_scanned_id).filter(
                NameI18nScanProgress.entity_type == entity_type,
            ).first()
            return row.last_scanned_id if row else 0

    def update_scan_progress(self, entity_type: str, last_scanned_id: int) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(NameI18nScanProgress).values(
                entity_type=entity_type,
                last_scanned_id=last_scanned_id,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[NameI18nScanProgress.entity_type.key],
                set_={
                    NameI18nScanProgress.last_scanned_id.key: insert_stmt.excluded.last_scanned_id,
                    NameI18nScanProgress.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def get_translation_status(self, entity_type: Optional[str] = None) -> Dict:
        with self.db.get_session() as session:
            query = session.query(
                NameI18n.entity_type,
                func.count(case((NameI18n.locale == 'en', 1))).label('total'),
                func.count(case((NameI18n.locale == 'zh', 1))).label('translated'),
            ).group_by(NameI18n.entity_type)
            if entity_type:
                query = query.filter(NameI18n.entity_type == entity_type)
            rows = query.all()
            return {
                row.entity_type: {
                    'total':      row.total,
                    'translated': row.translated,
                    'pending':    row.total - row.translated,
                }
                for row in rows
            }

    def get_pending_mapping_items(self, entity_type: str, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            en_entry = aliased(NameI18n)
            zh_entry = aliased(NameI18n)
            return session.query(
                en_entry.entity_code,
                en_entry.name,
            ).outerjoin(
                zh_entry,
                (zh_entry.entity_type == en_entry.entity_type) &
                (zh_entry.entity_code == en_entry.entity_code) &
                (zh_entry.locale == 'zh'),
            ).filter(
                en_entry.entity_type == entity_type,
                en_entry.locale == 'en',
                zh_entry.id.is_(None),
            ).limit(limit).all()

    def get_all_zh_names(self) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                NameI18n.entity_code,
                NameI18n.name,
            ).filter(
                NameI18n.locale == 'zh',
            ).all()

    def get_zh_name(self, entity_code: str) -> Optional[Any]:
        with self.db.get_session() as session:
            return session.query(NameI18n.name).filter(
                NameI18n.entity_code == entity_code,
                NameI18n.locale == 'zh',
            ).first()

    def sync_scanned_data(self, names: List[Dict]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(NameI18n).values(names).on_conflict_do_nothing(
                index_elements=[
                    NameI18n.entity_type.key,
                    NameI18n.entity_code.key,
                    NameI18n.locale.key,
                ]
            )
            session.execute(insert_stmt)
