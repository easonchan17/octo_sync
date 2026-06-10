from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, ValidationError
from core.services.base_service import BaseService
from core.types.enums import BROAD_POSITION
from core.store.postgres.daos.fotmob import MatchDao, ActiveFixtureDao
from core.store.postgres.daos.common import FeedbackIssueDao, ChatConversationDao


class FeedbackIssueInput(BaseModel):
    title:       str
    description: str
    category:    Literal["data", "prediction", "display", "other"]
    severity:    Literal["low", "medium", "high"]
    match_code:  Optional[str] = None


class ToolService(BaseService):
    def __init__(self):
        super().__init__()
        self.match_dao        = MatchDao()
        self.fixture_dao      = ActiveFixtureDao()
        self.feedback_dao     = FeedbackIssueDao()
        self.conversation_dao = ChatConversationDao()

    def search_by_team(self, team_name: str, anchor_time: str, direction: str) -> Dict[str, Any]:
        anchor = datetime.fromisoformat(anchor_time)
        after  = direction == "after"
        fixtures = self.fixture_dao.search_by_team_name(
            team_name,
            start_time=anchor if after else None,
            end_time=None if after else anchor,
            ascending=after,
        )
        if not fixtures:
            return {"found": False, "message": f"未找到 {team_name} 相关赛程"}
        return {"found": True, "fixtures": [self._fixture_to_dict(f) for f in fixtures]}

    def search_by_league(self, league_id: int, anchor_time: str, direction: str) -> Dict[str, Any]:
        anchor = datetime.fromisoformat(anchor_time)
        after  = direction == "after"
        fixtures = self.fixture_dao.fixtures_by_league(
            league_id,
            from_time=anchor if after else None,
            to_time=None if after else anchor,
            ascending=after,
        )
        if not fixtures:
            return {"found": False, "message": "未找到该赛事相关赛程"}
        return {"found": True, "fixtures": [self._fixture_to_dict(f) for f in fixtures]}

    def get_match_lineup(self, match_code: str) -> Dict[str, Any]:
        rows = self.match_dao.get_match_lineup(match_code)
        if not rows:
            return {"found": False, "message": "暂无该比赛的阵容数据"}

        result = {}
        for row in rows:
            usual_id = row.get("usual_playing_position_id")
            position = row.get("position") or BROAD_POSITION.get(usual_id)
            result.setdefault(row["team_name"], []).append({
                "name":       row["player_name"],
                "position":   position,
                "role":       row.get("role"),
                "is_captain": row["is_captain"],
            })
        return {"found": True, "lineups": result}

    def submit_issue(self, conversation_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            validated = FeedbackIssueInput(**data)
        except ValidationError as e:
            return {"ok": False, "error": f"参数校验失败，请重新整理后再次提交: {e}"}

        user_id = self.conversation_dao.get_user_id(conversation_id) or ""
        self.feedback_dao.create(conversation_id, user_id, validated.model_dump())
        return {"ok": True, "message": "工单已提交"}

    @staticmethod
    def _fixture_to_dict(fixture) -> Dict[str, Any]:
        return {
            "match_code":   fixture.match_code,
            "league_name":  fixture.league_name,
            "kickoff_time": str(fixture.kickoff_time),
            "home_team":    fixture.home_team,
            "away_team":    fixture.away_team,
        }
