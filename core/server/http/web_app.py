import secrets
import time
from typing import Any
from fastapi import Depends, FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import JSONResponse
from core.config.env_manager import env_manager
from core.logger.logger_manager import LoggerManager
from core.server.http.controllers.system.model_controller import ModelController
from core.server.http.controllers.app.fixture_controller import FixtureController
from core.server.http.controllers.app.league_controller import LeagueController
from core.server.http.controllers.app.match_controller import MatchController
from core.server.http.controllers.system.cron_controller import CronController

class WebApp:
    def __init__(self) -> None:
        self.app = FastAPI(
            title="Octopus API",
            description="Octopus Sports API",
            version="1.0.0",
            docs_url=None,
            redoc_url=None,
            openapi_url=None
        )
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._setup_middleware()
        self._setup_routes()
        self._setup_docs_protection()

    @staticmethod
    def _verify_credentials(credentials: HTTPBasicCredentials = Depends(HTTPBasic())) -> str:
        correct_username = env_manager.DOCS_USERNAME
        correct_password = env_manager.DOCS_PASSWORD

        is_correct_username = secrets.compare_digest(credentials.username, correct_username)
        is_correct_password = secrets.compare_digest(credentials.password, correct_password)
        if not (is_correct_username and is_correct_password):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials.username

    def _setup_routes(self) -> None:
        @self.app.get("/health")
        async def health_check() -> dict[str, str]:
            return {"status": "healthy"}

        model_controller = ModelController()
        self.app.include_router(model_controller.router, prefix="/api", tags=["models"])

        fixture_controller = FixtureController()
        self.app.include_router(fixture_controller.router, prefix="/api", tags=["fixtures"])

        match_controller = MatchController()
        self.app.include_router(match_controller.router, prefix="/api", tags=["matches"])

        league_controller = LeagueController()
        self.app.include_router(league_controller.router, prefix="/api", tags=["leagues"])

        cron_controller = CronController()
        self.app.include_router(cron_controller.router, prefix="/api", tags=["cron"])

    def _setup_docs_protection(self) -> None:
        if not env_manager.docs_enabled:
            return

        @self.app.get("/openapi.json", include_in_schema=False)
        async def get_open_api_endpoint(username: str = Depends(self._verify_credentials)) -> JSONResponse:
            return JSONResponse(
                get_openapi(
                    title=self.app.title,
                    version=self.app.version,
                    description=self.app.description,
                    routes=self.app.routes,
                )
            )

        @self.app.get("/docs", include_in_schema=False)
        async def get_documentation(username: str = Depends(self._verify_credentials)) -> Any:
            return get_swagger_ui_html(
                openapi_url="/openapi.json",
                title=f"{self.app.title} - Swagger UI",
            )

        @self.app.get("/redoc", include_in_schema=False)
        async def get_redoc_documentation(username: str = Depends(self._verify_credentials)) -> Any:
            return get_redoc_html(
                openapi_url="/openapi.json",
                title=f"{self.app.title} - ReDoc",
            )

    def _setup_middleware(self) -> None:
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next) -> Any:
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time

            client_ip = request.client.host if request.client else "unknown"

            self.logger.info(
                f"{client_ip} - {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
            )

            return response

    def get_app(self) -> FastAPI:
        return self.app