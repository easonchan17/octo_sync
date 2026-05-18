from enum import Enum
from functools import cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvType(str, Enum):
    DEV = "dev"
    PROD = "prod"

class EnvManager(BaseSettings):
    ENV: EnvType = Field(..., description="Run environment")
    DOCS_USERNAME: Optional[str] = Field(default=None, description="HTTP Basic username for /docs and /redoc; set with DOCS_PASSWORD to enable docs")
    DOCS_PASSWORD: Optional[str] = Field(default=None, description="HTTP Basic password for docs; set with DOCS_USERNAME to enable docs")
    MATCH_CODE_SALT: str = Field(..., description="Salt for match code generation")
    TEAM_CODE_SALT: str = Field(..., description="Salt for team code generation")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False
    )

    @property
    def docs_enabled(self) -> bool:
        username = (self.DOCS_USERNAME or "").strip()
        password = (self.DOCS_PASSWORD or "").strip()
        return bool(username and password)

    @property
    def is_dev(self) -> bool:
        return self.ENV == EnvType.DEV

    @property
    def is_prod(self) -> bool:
        return self.ENV == EnvType.PROD

    @property
    def value(self) -> str:
        return self.ENV.value

@cache
def get_env_manager() -> EnvManager:
    return EnvManager()