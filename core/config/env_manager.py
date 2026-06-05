from enum import Enum
from functools import cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvType(str, Enum):
    DEV  = "dev"
    PROD = "prod"
    ML   = "ml"

class EnvManager(BaseSettings):
    ENV: EnvType = Field(..., description="Run environment")
    DOCS_USERNAME: Optional[str] = Field(default=None, description="HTTP Basic username for /docs and /redoc; set with DOCS_PASSWORD to enable docs")
    DOCS_PASSWORD: Optional[str] = Field(default=None, description="HTTP Basic password for docs; set with DOCS_USERNAME to enable docs")
    ADMIN_USERNAME: Optional[str] = Field(default=None, description="HTTP Basic username for admin data endpoints; set with ADMIN_PASSWORD to enable them")
    ADMIN_PASSWORD: Optional[str] = Field(default=None, description="HTTP Basic password for admin data endpoints; set with ADMIN_USERNAME to enable them")
    MATCH_CODE_SALT: str = Field(..., description="Salt for match code generation")
    TEAM_CODE_SALT: str = Field(..., description="Salt for team code generation")
    PLAYER_CODE_SALT: str = Field(..., description="Salt for player code generation")
    JWT_SECRET: str = Field(..., description="HS256 secret for signing and verifying user JWT tokens")
    TURNSTILE_SECRET: Optional[str] = Field(default=None, description="Cloudflare Turnstile secret key; skip verification if unset")
    BREVO_API_KEY: Optional[str] = Field(default=None, description="Brevo email API key")
    MAILJET_API_KEY: Optional[str] = Field(default=None, description="Mailjet API key")
    MAILJET_API_SECRET: Optional[str] = Field(default=None, description="Mailjet API secret")
    RESEND_API_KEY: Optional[str] = Field(default=None, description="Resend API key")
    MAIL_FROM_ADDRESS: Optional[str] = Field(default=None, description="Sender email address")
    MAIL_FROM_NAME: str = Field(default="Takatikigo", description="Sender display name")
    HTTP_HOST: str = Field(..., description="HTTP server bind host")
    HTTP_PORT: int = Field(..., description="HTTP server bind port")
    CORS_ALLOW_ORIGINS: Optional[str] = Field(default=None, description="Comma-separated allowed CORS origins for the browser frontend, or * for all")
    DB_URL: str = Field(..., description="Database connection URL, e.g. postgresql://user:password@localhost:5432/dbname")
    REDIS_URL: str = Field(..., description="Redis connection URL, e.g. redis://localhost:6379/0")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False
    )

    @property
    def cors_allow_origins(self) -> list:
        if not self.CORS_ALLOW_ORIGINS:
            return []
        return [origin.strip().rstrip("/") for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    @property
    def docs_enabled(self) -> bool:
        username = (self.DOCS_USERNAME or "").strip()
        password = (self.DOCS_PASSWORD or "").strip()
        return self.is_dev and bool(username and password)

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