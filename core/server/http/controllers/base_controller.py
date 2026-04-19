from fastapi import APIRouter
from core.logger.logger_manager import LoggerManager

class BaseController:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.router = APIRouter()

    def get_router(self) -> APIRouter:
        return self.router