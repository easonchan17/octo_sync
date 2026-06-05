import uuid
import litellm
from functools import cache
from typing import Any, AsyncIterator, Dict, Optional
from core.services.base_service import BaseService
from core.chat.graph import ChatGraph
from core.chat.llm.client import get_chat_llm_client
from core.store.postgres.daos.common import ChatConversationDao
from core.chat.llm.token_rate_limiter import get_token_rate_limiter


class ChatConversationService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self.conversation_dao   = ChatConversationDao()
        self.chat_llm_client    = get_chat_llm_client()
        self.token_rate_limiter = get_token_rate_limiter()
        self.chat_graph         = ChatGraph()
        self.graph              = None

    async def initialize(self) -> None:
        self.chat_llm_client.validate_environment()
        conn_string        = self.db.get_conn_string()
        min_size, max_size = self.db.get_checkpoint_pool_size()
        self.graph = await self.chat_graph.compile(
            conn_string=conn_string,
            min_size=min_size,
            max_size=max_size,
        )
        self.logger.info("ConversationService initialized")

    async def shutdown(self) -> None:
        await self.chat_graph.aclose()
        self.logger.info("ConversationService shut down")

    def create_conversation(self, user_id: str) -> str:
        conversation_id = str(uuid.uuid4())
        self.conversation_dao.create(conversation_id, user_id)
        return conversation_id

    def get_conversation_owner(self, conversation_id: str) -> Optional[str]:
        return self.conversation_dao.get_user_id(conversation_id)

    def build_user_content(self, text: str, image_b64: Optional[str] = None) -> list:
        return self.chat_llm_client.build_content(text, image_b64)

    async def stream(self, conversation_id: str, user_id: str, user_content: list) -> AsyncIterator[Dict[str, Any]]:
        user_tokens  = litellm.token_counter(
            model=self.chat_llm_client.model,
            messages=[{"role": "user", "content": user_content}],
        )
        reserved_tokens  = user_tokens * 5
        reserved_keys = await self.token_rate_limiter.reserve(
            user_id,
            reserved_tokens,
            self.chat_llm_client.max_tokens_per_hour,
            self.chat_llm_client.max_tokens_per_day,
        )
        total_actual = 0
        try:
            async for event in self.graph.astream_events(
                {
                    "messages":        [{"role": "user", "content": user_content}],
                    "conversation_id": conversation_id,
                },
                config={"configurable": {"thread_id": conversation_id}},
                version="v2"
            ):
                if event.get("event") == "on_chat_model_end":
                    output = event.get("data", {}).get("output")
                    usage  = getattr(output, "usage_metadata", None)
                    if usage:
                        total_actual += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                yield event
        finally:
            await self.token_rate_limiter.correct(reserved_keys, reserved_tokens, total_actual)


@cache
def get_chat_conversation_service() -> ChatConversationService:
    return ChatConversationService()
