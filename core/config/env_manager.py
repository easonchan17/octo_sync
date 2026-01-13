from enum import Enum
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvType(str, Enum):
    DEV = "dev"
    PROD = "prod"
    ML = "ml"

class EnvManager(BaseSettings):
    ENV: EnvType = Field(..., description="Run environment")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False
    )

    @property
    def is_dev(self) -> bool:
        return self.ENV == EnvType.DEV

    @property
    def is_ml(self) -> bool:
        return self.ENV == EnvType.ML

    @property
    def is_prod(self) -> bool:
        return self.ENV == EnvType.PROD

    @property
    def value(self) -> str:
        return self.ENV.value

@lru_cache()
def get_env_manager() -> EnvManager:
    return EnvManager()

env_manager = get_env_manager()