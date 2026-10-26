import asyncio
from typing import Any, TypedDict, Annotated, Optional
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from core.chat.llm import get_llm_client
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from core.chat.graph.tools import TOOLS, execute_tool
from core.chat.llm.prompts import build_system_prompt


class ChatState(TypedDict):
    conversation_id: str
    messages:        Annotated[list, add_messages]


class ChatGraph:
    def __init__(self) -> None:
        self.llm_client = get_llm_client()
        self.llm_client.bind_tools(TOOLS)
        self.pool: Optional[AsyncConnectionPool] = None

    async def call_llm(self, state: ChatState) -> dict:
        response = await self.llm_client.acall_llm(state["messages"], build_system_prompt())
        return {"messages": [response]}

    async def call_tools(self, state: ChatState) -> dict:
        last_message    = state["messages"][-1]
        conversation_id = state["conversation_id"]
        tool_calls      = getattr(last_message, "tool_calls", []) or []
        results = await asyncio.gather(*[
            asyncio.to_thread(self._run_tool, tool_call, conversation_id)
            for tool_call in tool_calls
        ])
        return {"messages": results}

    def _run_tool(self, tool_call: dict, conversation_id: str) -> ToolMessage:
        return ToolMessage(
            content=execute_tool(tool_call["name"], tool_call["args"], conversation_id),
            tool_call_id=tool_call["id"],
            name=tool_call["name"],
        )

    def route(self, state: ChatState) -> str:
        last_message = state["messages"][-1]
        return "call_tools" if getattr(last_message, "tool_calls", None) else END

    async def compile(self, conn_string: str, min_size: int = 2, max_size: int = 10) -> Any:
        self.pool = AsyncConnectionPool(
            conn_string,
            min_size=min_size,
            max_size=max_size,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )
        await self.pool.open()

        checkpointer = AsyncPostgresSaver(self.pool)
        await checkpointer.setup()

        graph = StateGraph(ChatState)
        graph.add_node("call_llm",   self.call_llm)
        graph.add_node("call_tools", self.call_tools)

        graph.set_entry_point("call_llm")
        graph.add_conditional_edges("call_llm", self.route, {
            "call_tools": "call_tools",
            END:          END,
        })
        graph.add_edge("call_tools", "call_llm")

        return graph.compile(checkpointer=checkpointer)

    async def aclose(self) -> None:
        if self.pool is not None:
            await self.pool.close()
