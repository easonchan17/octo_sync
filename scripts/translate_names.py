import sys
import json
import argparse
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if Path('.').resolve() != Path(__file__).resolve().parents[1]:
    sys.exit(f"Must be run from project root: {Path(__file__).resolve().parents[1]}")

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from core.config.config_manager import get_config_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager
from core.chat.llm import get_chat_llm_client
from core.store.postgres.daos.common import NameI18nDao


SYSTEM_PROMPT = """你是足球数据国际化助手，负责为球队和联赛建立中文名称映射。

工作流程：
1. 使用 query_translation_status 查询翻译进度，展示摘要后等待用户指示
2. 用户明确说"开始翻译 team/league"后，再使用 fetch_unmapped_names 获取一批待翻译条目（每批不超过 50 条）
   - 如需查看已跳过条目，使用 fetch_skipped_names；对其中可翻译的条目，用 save_translations 保存（会覆盖跳过标记）
3. 将英文名翻译成中文，必须同时展示以下两个分区（即使某分区为空也要显示"（无）"）：
   - 【已翻译】列出 entity_code、英文名、中文译名
   - 【无把握，已跳过】列出 entity_code、英文名
4. 用户确认后同时调用 save_translations 保存译名、调用 mark_skipped 标记跳过条目，否则不保存
5. 重复直至完成

输出规范：
- 不使用任何 emoji 或特殊符号

翻译规范：
- 优先使用国内主流媒体通用译名（如"曼城"、"英超"、"西甲"）
- 联赛名称不加"联赛"后缀（"英超"而非"英超联赛"，"西甲"而非"西甲联赛"）
- 无把握的名称不要包含在 save_translations 中，但必须通过 mark_skipped 标记，避免下次重复出现
- 每批处理不超过 50 条，保证翻译质量
- 未经用户确认，绝不调用 save_translations
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_translation_status",
            "description": "查询各实体类型的翻译进度，返回已翻译和待翻译数量",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["team", "league"],
                        "description": "实体类型，不传则查询全部",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_unmapped_names",
            "description": "获取一批尚无中文名的实体，用于翻译",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["team", "league"],
                        "description": "实体类型",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "每批数量，最大 50，默认 30",
                    },
                },
                "required": ["entity_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_skipped_names",
            "description": "获取已标记为跳过的条目列表，可用于重新翻译",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["team", "league"],
                        "description": "实体类型",
                    },
                },
                "required": ["entity_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_skipped",
            "description": "将无法翻译的条目标记为跳过，避免下次重复出现，必须在用户确认后调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity_type": {"type": "string"},
                                "entity_code": {"type": "string"},
                            },
                            "required": ["entity_type", "entity_code"],
                        },
                    }
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_translations",
            "description": "将翻译结果保存到数据库，必须在用户明确确认后才能调用。仅包含确定的中文译名，不确定的条目不要传入",
            "parameters": {
                "type": "object",
                "properties": {
                    "translations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity_type": {"type": "string"},
                                "entity_code": {"type": "string"},
                                "name_zh":     {"type": "string"},
                            },
                            "required": ["entity_type", "entity_code", "name_zh"],
                        },
                    }
                },
                "required": ["translations"],
            },
        },
    },
]


class TranslationState(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph():
    dao = NameI18nDao()
    llm = get_chat_llm_client().build_llm(max_tokens=4096).bind_tools(TOOLS)

    def agent(state: TranslationState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    def tool_executor(state: TranslationState) -> dict:
        last    = state["messages"][-1]
        results = []
        for tool_call in last.tool_calls:
            result = _execute_tool(dao, tool_call["name"], tool_call["args"])
            results.append(ToolMessage(
                content=result,
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
            ))
        return {"messages": results}

    def route(state: TranslationState) -> str:
        last = state["messages"][-1]
        return "tool_executor" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(TranslationState)
    graph.add_node("agent",         agent)
    graph.add_node("tool_executor", tool_executor)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route, {"tool_executor": "tool_executor", END: END})
    graph.add_edge("tool_executor", "agent")

    return graph.compile(checkpointer=MemorySaver())


def _execute_tool(dao: NameI18nDao, name: str, args: dict) -> str:
    try:
        if name == "query_translation_status":
            return json.dumps(dao.get_translation_status(args.get("entity_type")))

        if name == "fetch_unmapped_names":
            limit = min(args.get("limit", 30), 50)
            rows  = dao.get_pending_mapping_items(args["entity_type"], limit)
            return json.dumps({
                "entity_type": args["entity_type"],
                "count":       len(rows),
                "items":       [{"entity_code": row.entity_code, "name": row.name} for row in rows],
            })

        if name == "mark_skipped":
            records = [
                {
                    "entity_type": item["entity_type"],
                    "entity_code": item["entity_code"],
                    "locale":      "zh",
                    "name":        "",
                }
                for item in args["items"]
            ]
            dao.sync_scanned_data(records)
            return json.dumps({"ok": True, "skipped": len(records)})

        if name == "fetch_skipped_names":
            rows = dao.get_skipped_names(args["entity_type"])
            return json.dumps({
                "entity_type": args["entity_type"],
                "count":       len(rows),
                "items":       [{"entity_code": row.entity_code, "name": row.name} for row in rows],
            })

        if name == "save_translations":
            records = [
                {
                    "entity_type": t["entity_type"],
                    "entity_code": t["entity_code"],
                    "locale":      "zh",
                    "name":        t["name_zh"],
                }
                for t in args["translations"]
            ]
            dao.upsert_zh_names(records)
            return json.dumps({"ok": True, "saved": len(records)})

    except Exception as e:
        print(f"[tool:{name}] {e}", file=sys.stderr)
        return json.dumps({"error": str(e)})

    return json.dumps({"error": f"unknown tool: {name}"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", type=str, default="configs/config.yml")
    args = parser.parse_args()

    get_config_manager().load_config(args.config)
    get_postgresql_manager().startup()

    compiled = build_graph()
    config   = {"configurable": {"thread_id": "translate_names"}}

    print("足球数据翻译助手，输入 quit 退出\n")

    result   = compiled.invoke({"messages": [HumanMessage(content="查询当前各实体类型的翻译进度，展示摘要即可，不要开始翻译")]}, config)
    last_msg = result["messages"][-1]
    if last_msg.content:
        print(f"\n{last_msg.content}\n")

    while True:
        user_input = input(">>> ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        result   = compiled.invoke({"messages": [HumanMessage(content=user_input)]}, config)
        last_msg = result["messages"][-1]
        if last_msg.content:
            print(f"\n{last_msg.content}\n")


if __name__ == "__main__":
    main()
