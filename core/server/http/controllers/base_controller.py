from fastapi import APIRouter
from core.logger.logger_manager import get_logger_manager

class BaseController:
    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.router = APIRouter()

    def get_router(self) -> APIRouter:
        return self.router