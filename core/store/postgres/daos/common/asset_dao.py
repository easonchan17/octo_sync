import traceback
from datetime import timedelta
from typing import List, Any, Dict, Optional
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.asset import Asset, AssetScanProgress
from core.store.postgres.models.common.league import SiteLeague
from core.store.postgres.models.fotmob.fixture import Fixture as FotmobFixture
from ..base_dao import BaseDao

class AssetDao(BaseDao):
    def get_fotmob_pending_fetch_teams(self, last_id: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                FotmobFixture.id,
                FotmobFixture.home_id,
                FotmobFixture.home_code,
                FotmobFixture.away_id,
                FotmobFixture.away_code,
            ).filter(
                FotmobFixture.id > last_id,
            ).order_by(FotmobFixture.id.asc()).all()

    def get_pending_fetch_leagues(self, site_name: str, last_id: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                SiteLeague.id,
                SiteLeague.league_id,
                SiteLeague.ref_league_id,
            ).filter(
                SiteLeague.site_name == site_name,
                SiteLeague.ref_league_id > 0,
                SiteLeague.id > last_id,
            ).order_by(SiteLeague.id.asc()).all()


    def get_pending_fetch_items(self, site_name: str) -> List[Any]:
        with self.db.get_session() as session:
            return (
                session.query(
                    Asset.source_url,
                    Asset.asset_type,
                    Asset.entity_type,
                    Asset.asset_usage,
                    Asset.file_name,
                    Asset.file_ext,
                    Asset.fetch_attempts,
                )
                .filter(Asset.source_site == site_name, Asset.next_fetch_at <= func.now())
                .order_by(Asset.next_fetch_at.asc())
                .all()
            )

    def mark_as_fetched(self, source_url: str) -> None:
        with self.db.get_session() as session:
            session.query(Asset).filter(Asset.source_url == source_url).update(
                {
                    Asset.is_fetched: True,
                    Asset.next_fetch_at: None,
                    Asset.last_fetch_error: None,
                    Asset.updated_at: func.now(),
                },
                synchronize_session=False
            )

    def mark_fetch_failed(self, source_url: str, fetch_interval: Optional[timedelta] = None, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()

        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else func.now()

        with self.db.get_session() as session:
            session.query(Asset).filter(Asset.source_url == source_url).update(
                {
                    Asset.is_fetched: False,
                    Asset.fetch_attempts: Asset.fetch_attempts + 1,
                    Asset.next_fetch_at: next_fetch_at,
                    Asset.last_fetch_error: error_msg[:2000],
                    Asset.updated_at: func.now(),
                },
                synchronize_session=False
            )

    def get_scan_progress(self, site_name: str, asset_type: str, entity_type: str, asset_usage: str) -> int:
        with self.db.get_session() as session:
            row = session.query(AssetScanProgress.last_scanned_id).filter(
                AssetScanProgress.site_name == site_name,
                AssetScanProgress.asset_type == asset_type,
                AssetScanProgress.entity_type == entity_type,
                AssetScanProgress.asset_usage == asset_usage,
            ).first()
            return row.last_scanned_id if row else 0

    def update_scan_progress(self, site_name: str, asset_type: str, entity_type: str, asset_usage: str, last_scanned_id: int) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(AssetScanProgress).values(
                site_name=site_name,
                asset_type=asset_type,
                entity_type=entity_type,
                asset_usage=asset_usage,
                last_scanned_id=last_scanned_id,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[
                    AssetScanProgress.site_name.key,
                    AssetScanProgress.asset_type.key,
                    AssetScanProgress.entity_type.key,
                    AssetScanProgress.asset_usage.key,
                ],
                set_={
                    AssetScanProgress.last_scanned_id.key: insert_stmt.excluded.last_scanned_id,
                    AssetScanProgress.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)


    def sync_scanned_data(self, assets: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(Asset).values(assets).on_conflict_do_nothing(
                index_elements=[Asset.source_url.key]
            )
            session.execute(insert_stmt)
