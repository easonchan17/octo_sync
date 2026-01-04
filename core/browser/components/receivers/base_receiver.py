import json
from typing import Any, Optional
from abc import ABC, abstractmethod
from core.logger.logger_manager import LoggerManager

class BaseReceiver(ABC):
    def __init__(self):
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.content_types = [
            'application/json'
        ]

        self.charsets = [
            'utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'big5',
            'latin-1', 'cp1252', 'iso-8859-1', 'ascii',
            'utf-16le', 'utf-16be', 'utf-32le', 'utf-32be'
        ]

    @abstractmethod
    async def process(self, *args, **kwargs) -> Optional[Any]:
        pass

    async def wait_for_ready(self, page_context: Any, selector: str, timeout: float) -> None:
        if not selector:
            return

        try:
            await page_context.wait_for_selector(selector, timeout=timeout*1000, state='attached')
        except Exception:
            pass

    async def decode_json_body(self, response: Any) -> Optional[Any]:
        try:
            mime_type, body = await self._decode_body(response)
            if mime_type != 'application/json':
                self.logger.error(f"Failed to parse json from {mime_type}")
                return None

            if not body:
                return None

            return json.loads(body)
        except Exception as e:
            self.logger.error(f"Failed to decode body to json: {e}")
            return None

    async def _decode_body(self, response: Any) -> tuple[str, str]:
        if not response:
            self.logger.error(f"Invalid response {response}")
            return None, None

        body = await response.body()
        if not body:
            self.logger.error(f"Failed to get body from response {response}")
            return None, None

        mime_type, header_charset = self._extract_content_info(response)
        if header_charset and self._try_decode(body, header_charset):
            return mime_type, body.decode(header_charset)

        for charset in self.charsets:
            if charset != header_charset and self._try_decode(body, charset):
                return mime_type, body.decode(charset)

        self.logger.error(f"Failed to decode body {response}: {body}")
        return mime_type, body

    def _extract_content_info(self, response: Any) -> tuple[str, str]:
        mimetype = ''
        charset = ''

        # Example: Content-Type: text/html; charset=utf-8; charset=gbk
        content_type = response.headers.get('content-type', '').lower()
        if not content_type:
            return mimetype, charset

        parts = [p.strip() for p in content_type.split(';') if p.strip()]
        if not parts:
            return mimetype, charset

        mimetype = parts[0]
        for p in parts[1:]:
            if p.startswith('charset='):
                charset = p.split('=', 1)[1].strip().strip('"\'')
                break

        return mimetype, charset

    def _try_decode(self, body: bytes, encoding: str) -> bool:
        if not body or not encoding:
            return False

        try:
            body.decode(encoding)
            return True
        except Exception:
            return False
