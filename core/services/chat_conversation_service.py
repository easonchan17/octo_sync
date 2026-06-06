import litellm
import uuid_utils
from datetime import datetime, timedelta, timezone
from functools import cache
from typing import Any, AsyncIterator, Dict, List, Optional
from core.services.base_service import BaseService
from core.chat.graph import ChatGraph
from core.chat.llm.client import get_chat_llm_client
from core.store.postgres.daos.common import ChatConversationDao
from core.chat.llm.token_rate_limiter import get_token_rate_limiter


class ChatConversationService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self.conversation_dao   = ChatConversationDao()
        self.chat_graph         = ChatGraph()
        self.chat_llm_client    = get_chat_llm_client()
        self.token_rate_limiter = get_token_rate_limiter()
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

    def get_or_create_conversation(self, user_id: str) -> str:
        existing = self.conversation_dao.get_pending_by_user(user_id)
        if existing:
            return existing

        conversation_id = f"cov_{uuid_utils.uuid7()}"
        self.conversation_dao.create(conversation_id, user_id)
        return conversation_id

    def get_conversations(self, user_id: str) -> List[Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        return self.conversation_dao.get_by_user(user_id, cutoff)

    def get_user_id(self, conversation_id: str) -> Optional[str]:
        return self.conversation_dao.get_user_id(conversation_id)

    def update_title(self, conversation_id: str, title: str) -> None:
        self.conversation_dao.update_title(conversation_id, title)

    async def generate_title(self, conversation_id: str) -> Optional[str]:
        def extract_text(content) -> str:
            if isinstance(content, str):
                return content
            return next((part["text"] for part in content if isinstance(part, dict) and part.get("type") == "text"), "")

        config         = {"configurable": {"thread_id": conversation_id}}
        state          = await self.graph.aget_state(config)
        messages       = state.values.get("messages", []) if state else []
        human_messages = [msg for msg in messages if msg.type == "human"]
        ai_messages    = [msg for msg in messages if msg.type == "ai" and not getattr(msg, "tool_calls", None)]
        if len(human_messages) != 1 or len(ai_messages) != 1:
            return None

        user_text = extract_text(human_messages[0].content)
        ai_text   = extract_text(ai_messages[0].content)
        fallback  = user_text[:20] or "未命名"

        try:
            prompt = (
                "你是一个专用于为聊天会话生成标题的助手。\n"
                "请根据以下对话内容，提炼出一个极其简练的会话标题。\n\n"
                "【严格约束】\n"
                "1. 忽略「你好」「在吗」等无意义的寒暄，直接提炼核心意图。\n"
                "2. 语言与用户输入的语言保持一致。\n"
                "3. 长度严格控制：中文不超过15个字，英文不超过10个单词。\n"
                "4. 格式极其严格：只返回标题纯文本，绝对不要带有标题等前缀，绝对不要包含任何引号、句号或标点符号。\n\n"
                "【对话内容】\n"
                f"用户：{user_text[:300]}\n"
                f"助手：{ai_text[:200]}\n\n"
                "标题："
            )
            response = await litellm.acompletion(
                model=self.chat_llm_client.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=30,
                temperature=0.3,
            )
            content = response.choices[0].message.content
            return content.strip() or fallback
        except Exception as e:
            self.logger.error(f"Failed to generate title for conversation={conversation_id}: {e}")
            return fallback

    def build_content(self, text: str, image_b64: Optional[str] = None) -> list:
        return self.chat_llm_client.build_content(text, image_b64)

    async def get_messages(self, conversation_id: str) -> List[Any]:
        config = {"configurable": {"thread_id": conversation_id}}
        state = await self.graph.aget_state(config)
        if not state:
            return []

        return state.values.get("messages", [])

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
