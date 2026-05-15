import traceback
from datetime import timedelta
from typing import List, Any, Dict, Optional
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.asset import Asset
from ..base_dao import BaseDao


class AssetDao(BaseDao):
    def insert_assets(self, assets: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(Asset).values(assets).on_conflict_do_nothing(
                index_elements=[Asset.source_url.key]
            )
            session.execute(insert_stmt)

    def get_pending_fetch_items(self, site_name: str) -> List[Any]:
        with self.db.get_session() as session:
            return (
                session.query(
                    Asset.source_url,
                    Asset.source_site,
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
