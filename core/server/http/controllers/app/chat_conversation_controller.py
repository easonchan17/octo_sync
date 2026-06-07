import json
import base64
import uuid_utils
import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
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
    ConversationSummaryResponse,
    ConversationMessageResponse,
)

class ChatConversationController(BaseController):
    MAX_MESSAGE_SIZE     = 512 * 1024
    MAX_MESSAGES_PER_MIN = 10
    AUTH_TIMEOUT_SECONDS = 10

    def __init__(self) -> None:
        super().__init__()
        self.conversation_service = get_chat_conversation_service()
        self.auth_service         = get_auth_service()
        self.redis_manager        = get_redis_manager()

        self.router.get("/v1/conversations", response_model=List[ConversationSummaryResponse])(self.get_conversations)
        self.router.get("/v1/conversations/{conversation_id}", response_model=List[ConversationMessageResponse])(self.get_conversation)
        self.router.websocket("/v1/ws")(self.connect)

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

    async def connect(self, websocket: WebSocket) -> None:
        if not self.auth_service.is_origin_allowed(websocket.headers.get("origin", "")):
            await websocket.close(code=4403)
            return

        await websocket.accept()

        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=self.AUTH_TIMEOUT_SECONDS)
            msg = json.loads(raw)
            if msg.get("type") != "chat:auth":
                await websocket.close(code=4401)
                return
            user_id = await self.auth_service.get_user_id(msg.get("token", ""))
        except WebSocketDisconnect:
            return
        except Exception:
            await websocket.close(code=4401)
            return

        conn_id = f"con_{uuid_utils.uuid7()}"
        redis = self.redis_manager.get_client()
        async with redis.pubsub() as pubsub:
            await pubsub.subscribe(f"ws:kick:{user_id}")
            await redis.publish(f"ws:kick:{user_id}", conn_id)

            listen_task   = asyncio.create_task(self._listen_kick(websocket, pubsub, conn_id))
            messages_task = asyncio.create_task(self._handle_messages(websocket, user_id))

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
        except Exception as e:
            self.logger.warning(f"_listen_kick exited unexpectedly: {e}")

    async def _handle_messages(
        self,
        websocket: WebSocket,
        user_id: str,
    ) -> None:
        async def try_update_title(cid: str) -> None:
            try:
                title = await self.conversation_service.generate_title(cid)
                if title:
                    self.conversation_service.update_title(cid, title)
                    await self._send_message(websocket, "chat", "title_updated", conversation_id=cid, title=title)
            except Exception as e:
                self.logger.error(f"Failed to update title conversation={cid}: {e}", exc_info=True)

        validated_conversations: set   = set()
        needs_title:             bool  = False
        recent_message_times:    deque = deque()
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    if len(raw) > self.MAX_MESSAGE_SIZE:
                        await self._send_message(websocket, "chat", "error", code="message_too_large")
                        continue

                    msg = json.loads(raw)
                    if msg.get("type") != "chat:message":
                        continue

                    now = datetime.now(timezone.utc)
                    cutoff = now - timedelta(minutes=1)
                    while recent_message_times and recent_message_times[0] < cutoff:
                        recent_message_times.popleft()

                    if len(recent_message_times) >= self.MAX_MESSAGES_PER_MIN:
                        await self._send_message(websocket, "chat", "error", code="rate_limit", message="消息发送过于频繁，请稍后再试")
                        continue
                    recent_message_times.append(now)

                    conversation_id = msg.get("conversation_id", "")
                    self.logger.debug(f"Received conversation_id={repr(conversation_id)!r} from user={user_id}")
                    if not conversation_id:
                        conversation_id = self.conversation_service.get_or_create_conversation(user_id)
                        self.logger.debug(f"Created/reused conversation_id={conversation_id} for user={user_id}")
                        await self._send_message(websocket, "chat", "conversation_created", conversation_id=conversation_id)
                        self.logger.debug(f"Sent conversation_created event: conversation_id={conversation_id}")
                        validated_conversations.add(conversation_id)
                        needs_title = True

                    if conversation_id not in validated_conversations:
                        owner = self.conversation_service.get_user_id(conversation_id)
                        if owner != user_id:
                            await self._send_message(websocket, "chat", "error", code="forbidden", conversation_id=conversation_id)
                            continue
                        validated_conversations.add(conversation_id)

                    content_text = msg.get("content", "").strip()
                    image_b64    = msg.get("image_b64")
                    if not content_text and not image_b64:
                        continue

                    if image_b64:
                        try:
                            base64.b64decode(image_b64, validate=True)
                        except Exception:
                            await self._send_message(websocket, "chat", "error", code="invalid_image")
                            continue

                    user_content = self.conversation_service.build_content(content_text, image_b64)
                    async for event in self.conversation_service.stream(conversation_id, user_id, user_content):
                        await self._dispatch_event(websocket, event)

                    if needs_title:
                        needs_title = False
                        asyncio.create_task(try_update_title(conversation_id))

                except WebSocketDisconnect:
                    raise
                except HourlyRateLimitExceeded:
                    now          = datetime.now(timezone.utc)
                    minutes_left = 60 - now.minute
                    await self._send_message(websocket, "chat", "error", code="rate_limit", conversation_id=conversation_id, message=f"每小时用量已达上限，请 {minutes_left} 分钟后再试")
                except DailyRateLimitExceeded:
                    now        = datetime.now(timezone.utc)
                    hours_left = 24 - now.hour
                    await self._send_message(websocket, "chat", "error", code="rate_limit", conversation_id=conversation_id, message=f"今日用量已达上限，请 {hours_left} 小时后再试")
                except Exception as e:
                    self.logger.error(f"WebSocket message error: {e}", exc_info=True)
                    await self._send_message(websocket, "chat", "error", message="Internal server error")

        except WebSocketDisconnect:
            pass

    async def _dispatch_event(self, websocket: WebSocket, event: dict) -> None:
        kind = event.get("event")
        name = event.get("name", "")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            token = getattr(chunk, "content", "") or "" if chunk else ""
            if token:
                await self._send_message(websocket, "chat", "token", content=token)

        elif kind == "on_chain_end" and name == "tool_executor":
            messages = event.get("data", {}).get("output", {}).get("messages", [])
            for message in messages:
                if getattr(message, "name", None) != ToolNames.SUBMIT_ISSUE:
                    continue
                result = json.loads(message.content)
                await self._send_message(websocket, "chat", "issue_submitted",
                    ok=result.get("ok", False),
                    message=result.get("message") or result.get("error", ""),
                )

        elif kind == "on_chain_end" and name == "LangGraph":
            await self._send_message(websocket, "chat", "done")

    async def _send_message(self, websocket: WebSocket, model: str, action: str, **data) -> None:
        await websocket.send_text(json.dumps({"type": f"{model}:{action}", **data}))
