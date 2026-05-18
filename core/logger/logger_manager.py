import os
import logging
import logging.config
import logging.handlers
from functools import cache
from typing import Any

class UvicornLogFilter(logging.Filter):
    def filter(self, record) -> bool:
        if record.name == "uvicorn.error":
            record.name = "uvicorn.server"
        return True

class LoggerManager:
    def __init__(self) -> None:
        self.logger = self.get_logger(self.__class__.__name__)
        self._set_root_config({
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'handlers': [
                {'kind': 'console'}
            ]
        })

    def setup(self, config: dict[str, Any]) -> None:
        self._set_root_config(config)
        self._set_uvicorn_config(config)

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)

    def _set_root_config(self, config: dict[str, Any]) -> None:
        level = config['level']
        format = config['format']

        log_level = getattr(logging, level.upper(), logging.INFO)
        log_formatter = logging.Formatter(format)
        log_handlers = self._build_handler_objects(
            config['handlers'],
            log_level,
            log_formatter
        )

        logging.basicConfig(
            level=log_level,
            format=format,
            handlers=log_handlers,
            force=True
        )
        self.logger.debug("Set root config")

    def _set_uvicorn_config(self, config: dict[str, Any]) -> None:
        level = config["level"]
        format = config["format"]

        handler_configs = self._build_handler_configs(
            config["handlers"],
            format,
            'output/logs/uvicorn.log'
        )
        handler_names = list(handler_configs.keys())

        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": format,
                },
                "access": {
                    "format": format,
                }
            },
            "handlers": handler_configs,
            "filters": {
                "uvicorn_rename_filter": {
                    "()": UvicornLogFilter
                }
            },
            "loggers": {
                "uvicorn.error": {
                    "handlers": handler_names,
                    "level": level.upper(),
                    "propagate": False,
                    "filters": ["uvicorn_rename_filter"]
                }
            },
            "root": {
                "handlers": handler_names,
                "level": level.upper(),
            }
        }

        logging.config.dictConfig(log_config)
        self.logger.debug("Set uvicorn config")

    def _build_handler_objects(self, handlers: list, log_level, log_formatter, default_file_path: str = 'output/logs/octopus.log') -> list:
        assert len(handlers) > 0, "handlers is required"

        log_handlers = []
        for handler in handlers:
            if handler['kind'] == 'console':
                console_handler = logging.StreamHandler()
                console_handler.setLevel(log_level)
                console_handler.setFormatter(log_formatter)
                log_handlers.append(console_handler)
            elif handler['kind'] == 'file':
                file_path = handler.get('path', default_file_path)
                max_bytes = handler.get('max_size', 10 * 1024 * 1024)
                backup_count = handler.get('backup_count', 5)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file_handler = logging.handlers.RotatingFileHandler(
                    file_path,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                file_handler.setLevel(log_level)
                file_handler.setFormatter(log_formatter)
                log_handlers.append(file_handler)
        return log_handlers

    def _build_handler_configs(self, handlers: list, format: str, default_file_path: str = 'output/logs/octopus.log') -> dict:
        handler_configs = {}
        for i, handler in enumerate(handlers):
            handler_name = f"handler_{i}"

            if handler['kind'] == 'console':
                handler_configs[handler_name] = {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout"
                }
            elif handler['kind'] == 'file':
                file_path = handler.get('path', default_file_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                handler_configs[handler_name] = {
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": file_path,
                    "maxBytes": handler.get('max_size', 10 * 1024 * 1024),
                    "backupCount": handler.get('backup_count', 5),
                    "encoding": "utf-8"
                }
        return handler_configs


@cache
def get_logger_manager() -> LoggerManager:
    return LoggerManager()
