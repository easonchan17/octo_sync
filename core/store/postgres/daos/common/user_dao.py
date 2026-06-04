from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.user import User
from ..base_dao import BaseDao


class UserDao(BaseDao):
    def upsert_by_email(self, email: str) -> None:
        with self.db.get_session() as session:
            session.execute(
                insert(User)
                .values(email=email, last_login=func.now())
                .on_conflict_do_update(
                    index_elements=[User.email],
                    set_={'last_login': func.now(), 'updated_at': func.now()}
                )
            )
