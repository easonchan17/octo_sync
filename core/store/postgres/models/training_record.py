from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, Float, Boolean, JSON
from .base_model import Base, StatusMixin, DictMixin, Status

class TrainingRecord(Base, StatusMixin, DictMixin):
    __tablename__ = 'training_records'
    __table_args__ = (
        Index('idx_training_records_create_at', 'create_at'),
        Index('idx_training_records_update_at', 'update_at'),
        Index('idx_training_records_model_type', 'model_type'),
        Index('idx_training_records_dataset_name', 'dataset_name'),
        Index('idx_training_records_best_score', 'best_score'),
        Index('idx_training_records_test_accuracy', 'test_accuracy'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    model_version = Column(String(50), nullable=False, unique=True)
    model_type = Column(String(50), nullable=False)
    model_path = Column(String(512), nullable=False)

    dataset_name = Column(String(256), nullable=False)
    feature_names = Column(JSON, nullable=False)

    best_params = Column(JSON, nullable=True)
    best_score = Column(Float, nullable=True)
    test_accuracy = Column(Float, nullable=True)
    is_production = Column(Boolean, nullable=False, default=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
