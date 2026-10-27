import json
from enum import StrEnum
from typing import Any, Dict
from core.services.tool_service import ToolService


class ToolNames(StrEnum):
    SUBMIT_ISSUE    = "submit_feedback_issue"
    SEARCH_BY_TEAM  = "search_by_team"
    SEARCH_BY_LEAGUE = "search_by_league"
    GET_LINEUPS     = "get_match_lineups"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": ToolNames.SEARCH_BY_TEAM,
            "description": "按球队查询赛程",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name":   {"type": "string", "description": "英文球队名，如 Argentina、Barcelona、Manchester United"},
                    "anchor_time": {"type": "string", "description": "参考时间点，ISO 8601 格式（如 2025-06-10T08:00:00+00:00）"},
                    "direction":   {"type": "string", "enum": ["after", "before"], "description": "after=查该时间点之后的比赛，before=查之前的比赛"}
                },
                "required": ["team_name", "anchor_time", "direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": ToolNames.SEARCH_BY_LEAGUE,
            "description": "按赛事查询赛程，传系统赛事ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "league_id":   {"type": "integer", "description": "系统赛事ID，如世界杯=301、欧冠=100、欧洲杯=401"},
                    "anchor_time": {"type": "string", "description": "参考时间点，ISO 8601 格式（如 2025-06-10T08:00:00+00:00）"},
                    "direction":   {"type": "string", "enum": ["after", "before"], "description": "after=查该时间点之后的比赛，before=查之前的比赛"}
                },
                "required": ["league_id", "anchor_time", "direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": ToolNames.GET_LINEUPS,
            "description": "查询一场比赛的双方首发和替补阵容。需先通过 search_by_team 或 search_by_league 获取 match_code，再调用本工具。适用于用户询问阵容、主力是否缺阵等问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_code": {"type": "string", "description": "比赛唯一标识，从 search_by_team 或 search_by_league 返回结果中获取"}
                },
                "required": ["match_code"]
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
        service = ToolService()
        if name == ToolNames.SEARCH_BY_TEAM:
            result = service.search_by_team(**args)
        elif name == ToolNames.SEARCH_BY_LEAGUE:
            result = service.search_by_league(**args)
        elif name == ToolNames.GET_LINEUPS:
            result = service.get_match_lineup(**args)
        elif name == ToolNames.SUBMIT_ISSUE:
            result = service.submit_issue(conversation_id, args)
        else:
            result = {"error": f"unknown tool: {name}"}
    except Exception as e:
        result = {"error": str(e)}
    return json.dumps(result)
