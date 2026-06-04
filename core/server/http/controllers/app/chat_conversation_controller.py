import json
from fastapi import WebSocket, WebSocketDisconnect, Depends
from core.services.chat_conversation_service import get_chat_conversation_service
from core.server.http.controllers.base_controller import BaseController
from core.server.http.auth import verify_token
from core.services.auth.auth_service import get_auth_service
from core.chat.graph.tools import ToolNames

class ChatConversationController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.conversation_service = get_chat_conversation_service()
        self.auth_service         = get_auth_service()

        self.router.post("/v1/conversations")(self.create_conversation)
        self.router.websocket("/v1/conversations/{conversation_id}")(self.chat)

    def create_conversation(self, user_id: str = Depends(verify_token)) -> dict:
        conversation_id = self.conversation_service.create_conversation(user_id)
        return {"conversation_id": conversation_id}

    async def chat(self, websocket: WebSocket, conversation_id: str) -> None:
        token = websocket.query_params.get("token", "")
        try:
            user_id = await self.auth_service.get_user_id(token)
        except Exception:
            await websocket.close(code=4401)
            return

        if self.conversation_service.get_conversation_owner(conversation_id) != user_id:
            await websocket.close(code=4403)
            return

        await websocket.accept()

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)

                    if msg.get("type") != "message":
                        continue

                    user_content = self.conversation_service.build_user_content(
                        msg.get("content", ""),
                        msg.get("image_b64")
                    )

                    async for event in self.conversation_service.stream(conversation_id, user_content):
                        await self._dispatch_event(websocket, event)

                except WebSocketDisconnect:
                    raise
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
