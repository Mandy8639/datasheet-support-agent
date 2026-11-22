"""Settings from environment variables (.env in development)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Admin role: ingestion and indexing scripts only.
    database_url: str = "postgresql://datasheet:change-me-admin@localhost:5433/datasheets"
    # Read-only role: everything the agent touches at answer time.
    agent_database_url: str = "postgresql://agent_ro:change-me-agent@localhost:5433/datasheets"

    openrouter_api_key: str = ""
    # Comma-separated OpenRouter model ids, tried in order (failover).
    openrouter_models: str = ""
    daily_spend_cap_usd: float = Field(default=1.00, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
