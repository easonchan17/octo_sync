import os
import time
from typing import Any
from fastapi import FastAPI, Request
from core.logger.logger_manager import LoggerManager
from core.server.controllers.site_controller import SiteController
from core.server.controllers.training_controller import TrainingController
from core.server.controllers.inference_controller import InferenceController
from core.server.controllers.fixture_controller import FixtureController
from core.server.controllers.cron_controller import CronController

class WebApp:
    def __init__(self) -> None:
        is_prod = os.getenv("ENV", "dev").lower() == "prod"

        self.app = FastAPI(
            title="Octopus API",
            description="Octopus Sports API",
            version="1.0.0",
            docs_url=None if is_prod else "/docs",
            redoc_url=None if is_prod else "/redoc",
            openapi_url=None if is_prod else "/openapi.json"
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

        training_controller = TrainingController()
        self.app.include_router(training_controller.router, prefix="/api", tags=["training"])

        inference_controller = InferenceController()
        self.app.include_router(inference_controller.router, prefix="/api", tags=["inference"])

        fixture_controller = FixtureController()
        self.app.include_router(fixture_controller.router, prefix="/api", tags=["fixtures"])

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