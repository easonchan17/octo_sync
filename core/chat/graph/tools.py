import json
from enum import Enum
from pydantic import BaseModel, ValidationError
from typing import Any, Dict, Literal, Optional
from datetime import datetime, timedelta, timezone
from core.store.postgres.daos.fotmob import ActiveFixtureDao, MatchDao
from core.store.postgres.daos.common import FeedbackIssueDao, ChatConversationDao, TrainingRecordDao


class ToolNames(str, Enum):
    SUBMIT_ISSUE     = "submit_feedback_issue"
    CHECK_PREDICTION = "check_prediction"
    SEARCH_FIXTURES  = "search_fixtures"


class FeedbackIssueModel(BaseModel):
    title:       str
    description: str
    category:    Literal["data", "prediction", "display", "other"]
    severity:    Literal["low", "medium", "high"]
    match_code:  Optional[str] = None


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": ToolNames.CHECK_PREDICTION,
            "description": "查询指定比赛的 AI 预测记录是否存在及预测内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_code": {"type": "string"}
                },
                "required": ["match_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": ToolNames.SEARCH_FIXTURES,
            "description": "查询指定球队的近期赛程，team_name 必须为英文标准名称",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name":  {"type": "string", "description": "英文球队名，如 Argentina、Barcelona、Manchester United"},
                    "days_ahead": {"type": "integer", "description": "查询未来天数，默认 30"}
                },
                "required": ["team_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": ToolNames.SUBMIT_ISSUE,
            "description": "用户明确确认后提交问题工单，绝不在用户确认前调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":       {"type": "string"},
                    "description": {"type": "string"},
                    "category":    {"type": "string", "enum": ["data", "prediction", "display", "other"]},
                    "severity":    {"type": "string", "enum": ["low", "medium", "high"]},
                    "match_code":  {"type": "string"}
                },
                "required": ["title", "description", "category", "severity"]
            }
        }
    },
]


def execute_tool(name: str, args: Dict[str, Any], conversation_id: str) -> str:
    try:
        if name == ToolNames.CHECK_PREDICTION:
            return _check_prediction(**args)
        if name == ToolNames.SEARCH_FIXTURES:
            return _search_fixtures(**args)
        if name == ToolNames.SUBMIT_ISSUE:
            return _submit_issue(conversation_id, args)
    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps({"error": f"unknown tool: {name}"})


def _submit_issue(conversation_id: str, args: Dict[str, Any]) -> str:
    try:
        validated = FeedbackIssueModel(**args)
    except ValidationError as e:
        return json.dumps({"ok": False, "error": f"参数校验失败，请重新整理后再次提交: {e}"})

    user_id = ChatConversationDao().get_user_id(conversation_id) or ""
    FeedbackIssueDao().create(conversation_id, user_id, validated.model_dump())
    return json.dumps({"ok": True, "message": "工单已提交"})



def _check_prediction(match_code: str) -> str:
    record = TrainingRecordDao().get_default()
    if record is None:
        return json.dumps({"found": False, "message": "暂无默认模型"})

    prediction = MatchDao().get_prediction(match_code, record.model_version)
    if prediction is None:
        return json.dumps({"found": False, "message": "该比赛暂无预测记录"})

    return json.dumps({
        "found":         True,
        "model_version": prediction.model_version,
        "home_prob":     prediction.home_prob,
        "draw_prob":     prediction.draw_prob,
        "away_prob":     prediction.away_prob,
        "prediction":    prediction.prediction,
    })


def _search_fixtures(team_name: str, days_ahead: int = 14) -> str:
    start_time = datetime.now(timezone.utc)
    end_time   = start_time + timedelta(days=days_ahead)
    fixtures   = ActiveFixtureDao().search_by_team_name(team_name, start_time, end_time)
    if not fixtures:
        return json.dumps({"found": False, "message": f"未找到 {team_name} 的近期赛程"})

    return json.dumps({
        "found":    True,
        "fixtures": [
            {
                "match_code":   fixture.match_code,
                "league_name":  fixture.league_name,
                "kickoff_time": str(fixture.kickoff_time),
                "home_team":    fixture.home_team,
                "away_team":    fixture.away_team,
            }
            for fixture in fixtures
        ]
    })
