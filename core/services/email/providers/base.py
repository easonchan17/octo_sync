from abc import ABC, abstractmethod
from typing import Optional

import httpx

from core.config.env_manager import EnvManager, get_env_manager
from core.logger.logger_manager import get_logger_manager


class EmailProvider(ABC):
    """Transactional email provider base class.

    Subclasses only declare per-vendor constants (name / api_url / daily_limit /
    ok_status) and implement build_payload(), plus headers() or auth() when the
    vendor needs credentials attached.

    Credentials are read straight from self.env.<FIELD>, so no env-var-name
    indirection is involved.

    Message copy (subject / content) is supplied by the caller, so this layer
    stays transport-only and knows nothing about OTP semantics.

    send() is a template method: request, success check and failure logging live
    here so every provider reports failures in the same shape.
    """

    name: str
    api_url: str
    daily_limit: int
    ok_status: tuple[int, ...] = (200, 201, 202)

    def __init__(self, env_manager: Optional[EnvManager] = None) -> None:
        self.env    = env_manager or get_env_manager()
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return True when the credentials required by this provider are present."""
        ...

    async def send(self, http_client: httpx.AsyncClient, to_email: str, subject: str, content: str) -> bool:
        if not self.is_enabled():
            self.logger.warning(f"{self.name} skipped: provider is not enabled")
            return False

        try:
            response = await http_client.post(
                self.api_url,
                headers=self.headers(),
                auth=self.auth(),
                json=self.build_payload(to_email, subject, content),
            )
            if response.status_code in self.ok_status:
                return True
        except Exception as e:
            self.logger.exception(f"{self.name} send failed: {type(e).__name__}: {e}")
            return False

        self.logger.warning(f"{self.name} send failed: status={response.status_code} body={response.text[:300]}")
        return False

    def headers(self) -> Optional[dict[str, str]]:
        return None

    def auth(self) -> Optional[tuple]:
        return None

    @abstractmethod
    def build_payload(self, to_email: str, subject: str, content: str) -> dict:
        ...
