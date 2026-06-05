import uuid_utils
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.common.user import User
from ..base_dao import BaseDao


class UserDao(BaseDao):
    def get_or_create(self, email: str) -> str:
        with self.db.get_session() as session:
            result = session.execute(
                insert(User)
                .values(email=email, uid=f"usr_{uuid_utils.uuid7()}", last_login=func.now())
                .on_conflict_do_update(
                    index_elements=[User.email],
                    set_={'last_login': func.now(), 'updated_at': func.now()}
                )
                .returning(User.uid)
            )
            return result.scalar_one()
