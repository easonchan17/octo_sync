import uvicorn
from core.server.web_app import WebApp
from core.utils.thread import Thread
from core.utils.singleton import Singleton
from core.config.config_manager import ConfigManager

class WebServer(Thread, Singleton): #TODO remove singleton, support multiple instances 8080 8000
    def __init__(self) -> None:
        super().__init__()
        self.host = None
        self.port = None
        self.server = None

    def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True
        super().stop()

    def _run(self) -> None:
        try:
            config = ConfigManager.get_instance().get_config("http")
            self.host = config["host"]
            self.port = config["port"]

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