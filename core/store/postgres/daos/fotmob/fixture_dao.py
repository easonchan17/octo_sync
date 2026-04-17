from sqlalchemy.types import Date
from typing import List, Dict, Any, Set, Optional
from sqlalchemy import or_, and_, func, cast
from sqlalchemy.dialects.postgresql import insert
from datetime import date, timedelta, datetime, timezone
from core.store.postgres.models.fotmob.fixture import Fixture, FixtureRaw
from ..base_dao import BaseDao

class FixtureDao(BaseDao):
    def get_pending_fetch_items(
        self,
        start_date: date,
        end_date: date
    ) -> List[Any]:
        with self.db.get_session() as session:
            rows = session.query(
                FixtureRaw.match_date,
                FixtureRaw.fetch_attempts,
                (FixtureRaw.next_fetch_at <= func.now()).label("is_fetchable")
            ).filter(
                FixtureRaw.match_date >= start_date,
                FixtureRaw.match_date <= end_date
            ).all()

            db_map = {row.match_date: row for row in rows}

            total_days = (end_date - start_date).days + 1
            result = []

            for i in range(total_days):
                dt = end_date - timedelta(days=i)
                row = db_map.get(dt)

                if row is None:
                    result.append((dt, 0))
                elif row.is_fetchable:
                    result.append((dt, row.fetch_attempts))

            return result

    def get_pending_parse_items(
        self,
        start_date: date,
        end_date: date,
        max_retries: int,
        limit: int
    ) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                FixtureRaw.match_date,
                FixtureRaw.json_body
            ).filter(
                FixtureRaw.match_date >= start_date,
                FixtureRaw.match_date <= end_date,
                FixtureRaw.is_fetched == True,
                FixtureRaw.is_parsed == False,
                FixtureRaw.parse_attempts < max_retries
            ).order_by(
                FixtureRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_not_modified(self, match_date: date, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(FixtureRaw).filter(
                FixtureRaw.match_date == match_date
            ).update({
                FixtureRaw.is_fetched: True,
                FixtureRaw.last_fetch_error: None,
                FixtureRaw.last_fetched_at: func.now(),
                FixtureRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None,
                FixtureRaw.total_fetch_count: FixtureRaw.total_fetch_count + 1,
                FixtureRaw.fetch_attempts: 0,
                FixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_fetched(self, match_date: date, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(FixtureRaw).filter(
                FixtureRaw.match_date == match_date
            ).update({
                FixtureRaw.is_fetched: True,
                FixtureRaw.last_fetch_error: None,
                FixtureRaw.last_fetched_at: func.now(),
                FixtureRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None,
                FixtureRaw.total_fetch_count: FixtureRaw.total_fetch_count + 1,
                FixtureRaw.is_parsed: False,
                FixtureRaw.last_parse_error: None,
                FixtureRaw.fetch_attempts: 0,
                FixtureRaw.parse_attempts: 0,
                FixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, match_date: date, error_msg: str, fetch_interval: Optional[timedelta]) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        with self.db.get_session() as session:
            insert_stmt = insert(FixtureRaw).values(
                match_date=match_date,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                json_body={},
                total_fetch_count=1,
                next_fetch_at=next_fetch_at
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[FixtureRaw.match_date],
                set_={
                    FixtureRaw.is_fetched: False,
                    FixtureRaw.last_fetch_error: (error_msg or "")[:2000],
                    FixtureRaw.fetch_attempts: FixtureRaw.fetch_attempts + 1,
                    FixtureRaw.total_fetch_count: FixtureRaw.total_fetch_count + 1,
                    FixtureRaw.next_fetch_at: next_fetch_at,
                    FixtureRaw.updated_at: func.now()
                }
            )
            session.execute(upsert_stmt)

    def mark_as_parsed(self, match_date: date, last_kickoff_time: datetime) -> None:
        with self.db.get_session() as session:
            session.query(FixtureRaw).filter(
                FixtureRaw.match_date == match_date
            ).update({
                FixtureRaw.last_kickoff_time: last_kickoff_time,
                FixtureRaw.is_parsed: True,
                FixtureRaw.last_parse_error: None,
                FixtureRaw.parse_attempts: 0,
                FixtureRaw.total_parse_count: FixtureRaw.total_parse_count + 1,
                FixtureRaw.last_parsed_at: func.now(),
                FixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, match_date: date, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(FixtureRaw).filter(
                FixtureRaw.match_date == match_date
            ).update({
                FixtureRaw.is_parsed: False,
                FixtureRaw.last_parse_error: (error_msg or "")[:2000],
                FixtureRaw.parse_attempts: FixtureRaw.parse_attempts + 1,
                FixtureRaw.total_parse_count: FixtureRaw.total_parse_count + 1,
                FixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(FixtureRaw).values(raw_data)

            update_values = {
                FixtureRaw.source_url.key: raw_data["source_url"],
                FixtureRaw.json_body.key: raw_data["json_body"],
                FixtureRaw.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[FixtureRaw.match_date.key],
                set_=update_values
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync fixture raw data completed. upserted: {upserted_count}")

    def sync_parsed_data(self, match_date: date, parsed_data: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(Fixture).values(parsed_data)
            assignment, where_clause = self.build_upsert_clauses(
                Fixture,
                insert_stmt,
                {
                    Fixture.id.key,
                    Fixture.created_at.key,
                    Fixture.match_id.key,
                    Fixture.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Fixture.match_id.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync match date={match_date} fixtures completed. upserted: {upserted_count}")

    def get_league_next_fixtures(self, site_name: str, league_ids: List[int], lookahead_hours: int) -> List[Any]:
        with self.db.get_session() as session:
            now = datetime.now(timezone.utc)
            lookahead = now + timedelta(hours=lookahead_hours)

            subquery = session.query(
                Fixture.league_id,
                func.min(Fixture.kickoff_time).label('next_kickoff')
            ).filter(
                Fixture.kickoff_time > now,
                Fixture.kickoff_time <= lookahead,
                Fixture.league_id.in_(league_ids)
            ).group_by(
                Fixture.league_id
            ).subquery()

            query = session.query(
                Fixture.league_id,
                Fixture.kickoff_time
            ).join(
                subquery,
                and_(
                    Fixture.league_id == subquery.c.league_id,
                    Fixture.kickoff_time == subquery.c.next_kickoff
                )
            )

            return query.all()

    def get_fixtures(self, start_time: datetime, end_time: datetime, league_ids: List[int]) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.id,
                Fixture.match_id,
                Fixture.league_id,
                Fixture.kickoff_time,
                Fixture.home_team,
                Fixture.away_team
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time <= end_time,
                Fixture.league_id.in_(league_ids)
            ).all()
