import json
from abc import ABC, abstractmethod
from typing import Any, Optional
from core.logger.logger_manager import LoggerManager

class BaseSender(ABC):
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    # Post_data=transformed_post_data
    def transform_post_data(self, request: Any, query_params: dict[str, Any]) -> str:
        if not query_params:
            self.logger.warning("No query parameters provided for POST data transformation.")
            return

        if request.method.upper() != 'POST':
            self.logger.warning("Request method is not POST; skipping POST data transformation.")
            return

        try:
            post_data = request.post_data
            post_data = json.loads(post_data)

            for key, value in query_params.items():
                self.logger.debug(f"Transform {key} to {value}")
                post_data[key] = value

            return json.dumps(post_data, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to transform request: {e}")

    # Url=transformed_get_data
    def transform_get_data(self, request: Any, query_params: dict[str, Any]) -> str:
        if not query_params:
            self.logger.warning("No query parameters provided for GET data transformation.")
            return

        if request.method.upper() != 'GET':
            self.logger.warning("Request method is not GET; skipping GET data transformation.")
            return

        try:
            url = request.url
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

            parsed_url = urlparse(url)
            get_data = parse_qs(parsed_url.query)

            for key, value in query_params.items():
                self.logger.debug(f"Transform {key} to {value}")
                get_data[key] = [value]

            query_data = urlencode(get_data, doseq=True)
            return urlunparse(parsed_url._replace(query=query_data))
        except Exception as e:
            self.logger.error(f"Failed to transform request: {e}")

    @abstractmethod
    def process(self, route: Any, request: Any, query_params: dict[str, Any]) -> bool:
        pass