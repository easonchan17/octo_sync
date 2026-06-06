import json
import uuid_utils
import asyncio
from datetime import datetime, timezone
from typing import List
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from core.services.chat_conversation_service import get_chat_conversation_service
from core.server.http.controllers.base_controller import BaseController
from core.server.http.auth import verify_token
from core.services.auth.auth_service import get_auth_service
from core.store.redis.redis_manager import get_redis_manager
from core.chat.graph.tools import ToolNames
from core.chat.llm.token_rate_limiter import HourlyRateLimitExceeded, DailyRateLimitExceeded
from core.server.http.schemas.api_models import (
    CreateConversationResponse,
    ConversationSummaryResponse,
    ConversationMessageResponse,
)

class ChatConversationController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.conversation_service = get_chat_conversation_service()
        self.auth_service         = get_auth_service()
        self.redis_manager        = get_redis_manager()

        self.router.post("/v1/conversations", response_model=CreateConversationResponse)(self.create_conversation)
        self.router.get("/v1/conversations", response_model=List[ConversationSummaryResponse])(self.get_conversations)
        self.router.get("/v1/conversations/{conversation_id}", response_model=List[ConversationMessageResponse])(self.get_conversation)
        self.router.websocket("/v1/conversations/{conversation_id}")(self.chat)

    def get_conversations(
        self,
        user_id: str = Depends(verify_token),
    ) -> List[ConversationSummaryResponse]:
        rows = self.conversation_service.get_conversations(user_id)
        return [ConversationSummaryResponse.model_validate(row) for row in rows]

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str = Depends(verify_token),
    ) -> List[ConversationMessageResponse]:
        owner = self.conversation_service.get_user_id(conversation_id)
        if owner is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if owner != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        messages = await self.conversation_service.get_messages(conversation_id)
        return [ConversationMessageResponse(role=msg.type, content=msg.content) for msg in messages]

    def create_conversation(self, user_id: str = Depends(verify_token)) -> CreateConversationResponse:
        conversation_id = self.conversation_service.get_or_create_conversation(user_id)
        return CreateConversationResponse(conversation_id=conversation_id)

    async def chat(self, websocket: WebSocket, conversation_id: str) -> None:
        try:
            user_id = await self.auth_service.get_user_id(
                websocket.query_params.get("token", "")
            )
        except Exception:
            await websocket.close(code=4401)
            return

        if self.conversation_service.get_user_id(conversation_id) != user_id:
            await websocket.close(code=4403)
            return

        await websocket.accept()

        conn_id = f"con_{uuid_utils.uuid7()}"
        redis   = self.redis_manager.get_client()
        async with redis.pubsub() as pubsub:
            await pubsub.subscribe(f"ws:kick:{user_id}")
            await redis.publish(f"ws:kick:{user_id}", conn_id)

            listen_task   = asyncio.create_task(self._listen_kick(websocket, pubsub, conn_id))
            messages_task = asyncio.create_task(self._handle_messages(websocket, conversation_id, user_id))

            try:
                await asyncio.wait(
                    {listen_task, messages_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                for task in (listen_task, messages_task):
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass

    async def _listen_kick(self, websocket: WebSocket, pubsub, conn_id: str) -> None:
        try:
            async for message in pubsub.listen():
                if message["type"] == "message" and message["data"] != conn_id:
                    await websocket.close(code=4008)
                    return
        except Exception:
            pass

    async def _handle_messages(
        self,
        websocket: WebSocket,
        conversation_id: str,
        user_id: str,
    ) -> None:
        async def try_update_title() -> None:
            try:
                title = await self.conversation_service.generate_title(conversation_id)
                if title:
                    self.conversation_service.update_title(conversation_id, title)
                    await websocket.send_text(json.dumps({"type": "title_updated", "conversation_id": conversation_id, "title": title}))
            except Exception as e:
                self.logger.error(f"Failed to update title conversation={conversation_id}: {e}", exc_info=True)

        title_pending = True
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                    if msg.get("type") != "message":
                        continue

                    content_text = msg.get("content", "").strip()
                    image_b64    = msg.get("image_b64")
                    if not content_text and not image_b64:
                        continue

                    user_content = self.conversation_service.build_content(content_text, image_b64)
                    async for event in self.conversation_service.stream(conversation_id, user_id, user_content):
                        await self._dispatch_event(websocket, event)

                    if title_pending:
                        title_pending = False
                        asyncio.create_task(try_update_title())

                except WebSocketDisconnect:
                    raise
                except HourlyRateLimitExceeded:
                    now          = datetime.now(timezone.utc)
                    minutes_left = 60 - now.minute
                    await websocket.send_text(json.dumps({"type": "error", "code": "rate_limit", "message": f"每小时用量已达上限，请 {minutes_left} 分钟后再试"}))
                except DailyRateLimitExceeded:
                    now        = datetime.now(timezone.utc)
                    hours_left = 24 - now.hour
                    await websocket.send_text(json.dumps({"type": "error", "code": "rate_limit", "message": f"今日用量已达上限，请 {hours_left} 小时后再试"}))
                except Exception as e:
                    self.logger.error(f"WebSocket message error conversation={conversation_id}: {e}", exc_info=True)
                    await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))

        except WebSocketDisconnect:
            pass

    async def _dispatch_event(self, websocket: WebSocket, event: dict) -> None:
        kind = event.get("event")
        name = event.get("name", "")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            token = getattr(chunk, "content", "") or "" if chunk else ""
            if token:
                await websocket.send_text(json.dumps({"type": "token", "content": token}))

        elif kind == "on_chain_end" and name == "tool_executor":
            messages = event.get("data", {}).get("output", {}).get("messages", [])
            for message in messages:
                if getattr(message, "name", None) != ToolNames.SUBMIT_ISSUE:
                    continue
                result = json.loads(message.content)
                await websocket.send_text(json.dumps({
                    "type":    "issue_submitted",
                    "ok":      result.get("ok", False),
                    "message": result.get("message") or result.get("error", "")
                }))

        elif kind == "on_chain_end" and name == "LangGraph":
            await websocket.send_text(json.dumps({"type": "done"}))
