import json
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Any
from core.logger.logger_manager import get_logger_manager

class BaseSender(ABC):
    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)

    def transform_post_data(
        self,
        request: Any,
        query_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not query_params:
            self.logger.warning("No query parameters provided for POST data transformation.")
            return None

        if request.method.upper() != 'POST':
            self.logger.warning("Request method is not POST; skipping POST data transformation.")
            return None

        try:
            post_data = request.post_data
            post_data = json.loads(post_data)

            for key, value in query_params.items():
                self.logger.debug(f"Transform {key} to {value}")
                post_data[key] = value

            return {
                'post_data': json.dumps(post_data, ensure_ascii=False)
            }
        except Exception as e:
            self.logger.error(f"Failed to transform request: {e}")
            return None

    def transform_get_data(
        self,
        request: Any,
        query_params: dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not query_params:
            self.logger.warning("No query parameters provided for GET data transformation.")
            return None

        if request.method.upper() != 'GET':
            self.logger.warning("Request method is not GET; skipping GET data transformation.")
            return None

        try:
            url = request.url
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

            parsed_url = urlparse(url)
            get_data = parse_qs(parsed_url.query)

            for key, value in query_params.items():
                self.logger.debug(f"Transform {key} to {value}")
                get_data[key] = [value]

            query_data = urlencode(get_data, doseq=True)
            return {
                'url': urlunparse(parsed_url._replace(query=query_data))
            }
        except Exception as e:
            self.logger.error(f"Failed to transform request: {e}")
            return None

    def disable_cache(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        headers["Cache-Control"] = "no-cache, no-store"
        headers["Pragma"] = "no-cache"

        keys_to_remove = ["if-modified-since", "if-none-match"]
        for key in keys_to_remove:
            if key in headers:
                del headers[key]

        return {"headers": headers}

    @abstractmethod
    def process(self, request: Any, query_params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        pass