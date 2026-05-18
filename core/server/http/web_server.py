import uvicorn
from functools import cache
from core.server.http.web_app import WebApp
from core.utils.thread import Thread
from core.config.config_manager import get_config_manager

class WebServer(Thread):
    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.server = None

    def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True
        super().stop()

    def _run(self) -> None:
        try:
            config = uvicorn.Config(
                WebApp().get_app(),
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False,
                use_colors=False,
                log_config=None
            )
            self.server = uvicorn.Server(config)
            self.server.run()
            self.server = None
        except Exception as e:
            self.logger.error(f"Error in web server: {e}")
        finally:
            self.logger.debug("web server stopped")


@cache
def get_web_server() -> WebServer:
    config = get_config_manager().get_config("http")
    return WebServer(host=config["host"], port=config["port"])