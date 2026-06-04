from sqlalchemy import Column, BigInteger, String, DateTime, Index
from ..base_model import Base


class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_updated_at', 'updated_at'),
        Index('idx_users_last_login', 'last_login'),
    )

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    email      = Column(String(255), nullable=False, unique=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
