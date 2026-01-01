from typing import List, Dict, Any, Set
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from core.store.postgres.models import Site, CompTeam, MatchCursor
from core.store.postgres.models.fotmob.fixture import Fixture
from ..base_synchronizer import BaseSynchronizer

class MatchCursorSynchronizer(BaseSynchronizer):
    def sync(self, fixtures: List[Dict[str, Any]], comp_code: str) -> None:
        if not fixtures:
            return

        fbref_site = self.get_site("fbref")
        if not fbref_site:
            self.logger.warning("fbref site not found, skip updating match_cursor")
            return

        with self.db.get_session(fbref_site.get_namespace()) as session:
            team_name_to_code = self._get_team_code_mapping(session, comp_code)
            if not team_name_to_code:
                self.logger.warning(f"No team code mapping found for comp_code={comp_code}")
                return

            all_team_codes = set(team_name_to_code.values())

            team_kickoff_times = {}
            for fixture in fixtures:
                kickoff_time = fixture.get(Fixture.kickoff_time.key)
                if not kickoff_time:
                    continue

                if isinstance(kickoff_time, str):
                    kickoff_time = datetime.fromisoformat(kickoff_time.replace('Z', '+00:00'))

                home_team = fixture.get(Fixture.home_team.key)
                away_team = fixture.get(Fixture.away_team.key)

                if home_team and home_team in team_name_to_code:
                    team_code = team_name_to_code[home_team]
                    current_time = team_kickoff_times.get(team_code)
                    if not current_time or kickoff_time > current_time:
                        team_kickoff_times[team_code] = kickoff_time

                if away_team and away_team in team_name_to_code:
                    team_code = team_name_to_code[away_team]
                    current_time = team_kickoff_times.get(team_code)
                    if not current_time or kickoff_time > current_time:
                        team_kickoff_times[team_code] = kickoff_time

            missing_teams = all_team_codes - set(team_kickoff_times.keys())
            if missing_teams:
                self.logger.warning(
                    f"Found {len(missing_teams)} teams without matches in fixtures for comp_code={comp_code}. "
                    f"These teams will not be updated: {missing_teams}"
                )

        with self.db.get_session() as public_session:
            for team_code in all_team_codes:
                if team_code in team_kickoff_times:
                    last_kickoff_time = team_kickoff_times[team_code]
                    insert_stmt = insert(MatchCursor).values(
                        comp_code=comp_code,
                        team_code=team_code,
                        last_kickoff_time=last_kickoff_time
                    )
                    insert_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=[MatchCursor.comp_code.key, MatchCursor.team_code.key],
                        set_={
                            MatchCursor.last_kickoff_time.key: last_kickoff_time,
                            MatchCursor.updated_at.key: func.now()
                        }
                    )
                    public_session.execute(insert_stmt)

            public_session.commit()

        updated_count = len(team_kickoff_times)
        total_count = len(all_team_codes)
        self.logger.info(
            f"Updated {updated_count}/{total_count} match cursors for comp_code={comp_code}"
        )

    def _get_team_code_mapping(self, session: Session, comp_code: str) -> Dict[str, str]:
        teams = session.query(CompTeam.team_name, CompTeam.team_code).filter(
            CompTeam.comp_code == comp_code
        ).all()

        return {team_name: team_code for team_name, team_code in teams}
