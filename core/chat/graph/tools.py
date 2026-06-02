import json
from enum import Enum
from pydantic import BaseModel, ValidationError
from typing import Any, Dict, Literal, Optional
from core.store.postgres.daos.fotmob import ActiveFixtureDao, MatchDao
from core.store.postgres.daos.common import FeedbackIssueDao, ChatConversationDao, TrainingRecordDao


class ToolNames(str, Enum):
    SUBMIT_ISSUE     = "submit_feedback_issue"
    CHECK_SYNC       = "check_sync_status"
    CHECK_PREDICTION = "check_prediction"
    SEARCH_SIMILAR   = "search_similar_issues"


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
            "name": ToolNames.CHECK_SYNC,
            "description": "查询指定比赛或日期的数据同步状态，包含抓取和解析是否成功",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_date": {"type": "string", "description": "格式 YYYY-MM-DD"},
                    "match_code": {"type": "string", "description": "比赛编码"}
                }
            }
        }
    },
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
            "name": ToolNames.SEARCH_SIMILAR,
            "description": "搜索是否存在相似的历史工单，避免重复提交",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"}
                },
                "required": ["description"]
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
        if name == ToolNames.CHECK_SYNC:
            return _check_sync_status(**args)
        if name == ToolNames.CHECK_PREDICTION:
            return _check_prediction(**args)
        if name == ToolNames.SEARCH_SIMILAR:
            return _search_similar_issues(**args)
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


def _check_sync_status(match_date: str = None, match_code: str = None) -> str:
    dao = ActiveFixtureDao()
    if match_code:
        fixture = dao.get_by_match_code(match_code)
        if fixture is None:
            return json.dumps({"found": False, "message": "比赛不存在"})

        return json.dumps({
            "found":        True,
            "match_id":     fixture.match_id,
            "kickoff_time": str(fixture.kickoff_time),
            "match_status": fixture.match_status,
        })

    return json.dumps({"message": "请提供 match_code 或 match_date"})


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


def _search_similar_issues(description: str) -> str:
    issues = FeedbackIssueDao().search_recent(description, limit=3)
    if not issues:
        return json.dumps({"found": False, "message": "未找到相似历史工单"})

    return json.dumps({
        "found":  True,
        "issues": [
            {"id": issue.id, "title": issue.title, "category": issue.category, "severity": issue.severity}
            for issue in issues
        ]
    })
