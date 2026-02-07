import time
from typing import Any
from fastapi import FastAPI, Request
from core.config.env_manager import env_manager
from core.logger.logger_manager import LoggerManager
from core.server.controllers.system.site_controller import SiteController
from core.server.controllers.system.task_controller import TaskController
from core.server.controllers.system.model_controller import ModelController
from core.server.controllers.app.prediction_controller import PredictionController
from core.server.controllers.app.fixture_controller import FixtureController
from core.server.controllers.app.league_controller import LeagueController
from core.server.controllers.system.cron_controller import CronController

class WebApp:
    def __init__(self) -> None:
        is_dev = env_manager.is_dev
        self.app = FastAPI(
            title="Octopus API",
            description="Octopus Sports API",
            version="1.0.0",
            docs_url="/docs" if is_dev else None,
            redoc_url="/redoc" if is_dev else None,
            openapi_url="/openapi.json" if is_dev else None
        )
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._setup_middleware()
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.get("/health")
        async def health_check() -> dict[str, str]:
            return {"status": "healthy"}

        site_controller = SiteController()
        self.app.include_router(site_controller.router, prefix="/api", tags=["sites"])

        task_controller = TaskController()
        self.app.include_router(task_controller.router, prefix="/api", tags=["tasks"])

        model_controller = ModelController()
        self.app.include_router(model_controller.router, prefix="/api", tags=["models"])

        prediction_controller = PredictionController()
        self.app.include_router(prediction_controller.router, prefix="/api", tags=["predictions"])

        fixture_controller = FixtureController()
        self.app.include_router(fixture_controller.router, prefix="/api", tags=["fixtures"])

        league_controller = LeagueController()
        self.app.include_router(league_controller.router, prefix="/api", tags=["leagues"])

        cron_controller = CronController()
        self.app.include_router(cron_controller.router, prefix="/api", tags=["cron"])

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