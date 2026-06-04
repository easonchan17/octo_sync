from fastapi import Request, HTTPException, status
from core.server.http.controllers.base_controller import BaseController
from core.server.http.schemas.api_models import SendCodeRequest, LoginRequest
from core.services.auth.otp_service import get_otp_service
from core.services.auth.auth_service import get_auth_service


class LoginController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.otp_service  = get_otp_service()
        self.auth_service = get_auth_service()

        self.router.post("/auth/send-code")(self.send_code)
        self.router.post("/auth/login")(self.login)

    async def send_code(self, body: SendCodeRequest, request: Request) -> dict:
        user_ip = request.headers.get("cf-connecting-ip") or request.client.host
        try:
            await self.otp_service.send_code(body.email, body.turnstileToken, user_ip)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        return {}

    async def login(self, body: LoginRequest) -> dict:
        try:
            token = await self.auth_service.login(body.email, body.code)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        return {"token": token}
