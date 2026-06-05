import asyncio
import litellm
from typing import TypedDict, Annotated, Optional
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from core.chat.llm.prompts import SYSTEM_PROMPT
from core.chat.llm import get_chat_llm_client
from langchain_core.messages import SystemMessage, ToolMessage, trim_messages, get_buffer_string
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from core.chat.graph.tools import TOOLS, execute_tool


class ChatState(TypedDict):
    conversation_id: str
    messages:        Annotated[list, add_messages]


class ChatGraph:
    def __init__(self) -> None:
        chat_llm_client         = get_chat_llm_client()
        self.llm                = chat_llm_client.build_llm().bind_tools(TOOLS)
        self.model              = chat_llm_client.model
        self.max_context_tokens = chat_llm_client.max_context_tokens
        self.pool: Optional[AsyncConnectionPool] = None

    def _count_tokens(self, messages: list) -> int:
        return litellm.token_counter(model=self.model, text=get_buffer_string(messages))

    async def agent(self, state: ChatState) -> dict:
        trimmed  = trim_messages(
            state["messages"],
            max_tokens=self.max_context_tokens,
            token_counter=self._count_tokens,
            strategy="last",
            start_on="human",
            allow_partial=False,
        )
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + trimmed
        response = await self.llm.ainvoke(messages)
        return {"messages": [response]}

    async def tool_executor(self, state: ChatState) -> dict:
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
        return "tool_executor" if getattr(last_message, "tool_calls", None) else END

    async def compile(self, conn_string: str, min_size: int = 2, max_size: int = 10):
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
        graph.add_node("agent",         self.agent)
        graph.add_node("tool_executor", self.tool_executor)

        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", self.route, {
            "tool_executor": "tool_executor",
            END:             END,
        })
        graph.add_edge("tool_executor", "agent")

        return graph.compile(checkpointer=checkpointer)

    async def aclose(self) -> None:
        if self.pool is not None:
            await self.pool.close()
