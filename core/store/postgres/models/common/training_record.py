from sqlalchemy.sql import func
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Index, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from ..base_model import Base, Status

class TrainingRecord(Base):
    __tablename__ = 'training_records'
    __table_args__ = (
        Index('idx_training_records_created_at', 'created_at'),
        Index('idx_training_records_updated_at', 'updated_at'),
        Index('idx_training_records_model_family', 'model_family'),
        Index('idx_training_records_model_type', 'model_type'),
        Index('idx_training_records_dataset_name', 'dataset_name'),
        Index('idx_training_records_train_score', 'train_score'),
        Index('idx_training_records_test_score', 'test_score')
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    model_version = Column(String(256), nullable=False, unique=True)
    model_family = Column(String(256), nullable=False)
    model_type = Column(String(256), nullable=False)
    model_path = Column(Text, nullable=False)

    dataset_name = Column(String(256), nullable=False)
    feature_names = Column(JSONB(none_as_null=True), nullable=False)

    training_params = Column(JSONB(none_as_null=True), nullable=False)

    best_params = Column(JSONB(none_as_null=True), nullable=False)
    train_score = Column(Float, nullable=False)
    test_score = Column(Float, nullable=False)
    is_recommended = Column(Boolean, nullable=False, default=False)
