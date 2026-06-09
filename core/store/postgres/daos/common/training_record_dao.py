from typing import List, Optional, Tuple
from core.store.postgres.models import TrainingRecord, Status
from ..base_dao import BaseDao


class TrainingRecordDao(BaseDao):
    def get_default(self, model_family: str) -> Optional[TrainingRecord]:
        with self.db.get_session() as session:
            record = session.query(TrainingRecord).filter(
                TrainingRecord.status == Status.ACTIVE.value,
                TrainingRecord.model_family == model_family,
            ).order_by(
                TrainingRecord.is_recommended.desc(),
                TrainingRecord.created_at.desc()
            ).first()

            if record:
                session.expunge(record)
            return record

    def get_by_version(self, version: str) -> TrainingRecord:
        with self.db.get_session() as session:
            record = session.query(TrainingRecord).filter(
                TrainingRecord.model_version == version,
                TrainingRecord.status == Status.ACTIVE.value
            ).first()

            if not record:
                raise ValueError(f"Model version {version} not found in database")

            session.expunge(record)
            return record

    def get_list(self, page: int, page_size: int) -> Tuple[int, List[TrainingRecord]]:
        with self.db.get_session() as session:
            query = session.query(TrainingRecord).filter(
                TrainingRecord.status == Status.ACTIVE.value
            ).order_by(
                TrainingRecord.created_at.desc()
            )

            total = query.count()
            records = query.offset((page - 1) * page_size).limit(page_size).all()

            session.expunge_all()
            return total, records
