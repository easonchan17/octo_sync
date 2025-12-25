from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, Float, JSON, Text
from ..base_model import Base, StatusMixin, DictMixin, Status

class TrainingRecord(Base, StatusMixin, DictMixin):
    __tablename__ = 'training_records'
    __table_args__ = (
        Index('idx_training_records_created_at', 'created_at'),
        Index('idx_training_records_updated_at', 'updated_at'),
        Index('idx_training_records_model_type', 'model_type'),
        Index('idx_training_records_dataset_name', 'dataset_name'),
        Index('idx_training_records_train_score', 'train_score'),
        Index('idx_training_records_test_score', 'test_score'),
        {'schema': 'public'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    model_version = Column(String(256), nullable=False, unique=True)
    model_type = Column(String(256), nullable=False)
    model_path = Column(Text, nullable=False)

    dataset_name = Column(String(256), nullable=False)
    feature_names = Column(JSON, nullable=False)

    training_params = Column(JSON, nullable=False)

    best_params = Column(JSON, nullable=False)
    train_score = Column(Float, nullable=False)
    test_score = Column(Float, nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
