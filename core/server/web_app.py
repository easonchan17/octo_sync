import time
from typing import Any
from fastapi import FastAPI, Request
from core.logger.logger_manager import LoggerManager
from core.server.controllers.site_controller import SiteController
from core.server.controllers.browser_controller import BrowserController
from core.server.controllers.training_controller import TrainingController
from core.server.controllers.inference_controller import InferenceController

class WebApp:
    def __init__(self) -> None:
        self.app = FastAPI()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._setup_middleware()
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.get("/")
        async def root() -> dict[str, str]:
            return {"message": "Octopus Extractor API is running"}

        @self.app.get("/health")
        async def health_check() -> dict[str, str]:
            return {"status": "healthy"}

        site_controller = SiteController()
        self.app.include_router(site_controller.router, prefix="/api", tags=["sites"])

        browser_controller = BrowserController()
        self.app.include_router(browser_controller.router, prefix="/api", tags=["browser"])

        training_controller = TrainingController()
        self.app.include_router(training_controller.router, prefix="/api", tags=["training"])

        inference_controller = InferenceController()
        self.app.include_router(inference_controller.router, prefix="/api", tags=["inference"])

    def _setup_middleware(self) -> None:
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next) -> Any:
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time

            self.logger.info(
                f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
            )

            return response

    def get_app(self) -> FastAPI:
        return self.app