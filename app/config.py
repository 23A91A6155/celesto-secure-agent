"""Application configuration and environment variable loading."""

import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,  # Do not read .env automatically to prevent accidental secret loading
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Celesto Sandbox Configuration
    CELESTO_PROVIDER: Literal["local", "cloud"] = Field(
        default="local",
        description="Execution provider for Celesto microVMs (local Firecracker or Celesto Cloud)",
    )
    CELESTO_API_KEY: str = Field(
        default="replace_with_your_celesto_api_key",
        description="API key for Celesto Cloud",
    )

    # LLM Configuration (Optional/Placeholder allows health & ledger to start)
    LLM_API_KEY: str = Field(
        default="replace_with_your_llm_api_key",
        description="API key for language model provider",
    )
    LLM_MODEL: str = Field(
        default="replace_with_supported_model",
        description="Model identifier for agent tasks",
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://app:app_password@localhost:5432/celesto_ledger",
        description="Database connection URL for run ledger",
    )

    # API Server Port
    API_PORT: int = Field(
        default=8080,
        description="HTTP port for trusted control plane",
    )

    # Operational settings
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    COMMAND_TIMEOUT_SECONDS: int = Field(default=30)
    MAX_STEP_COUNT: int = Field(default=10)
    MAX_OUTPUT_BYTES: int = Field(default=65536)
    MAX_COMMAND_LENGTH: int = Field(default=1024)

    # Workspace directory
    WORKSPACE_DIR: str = Field(default="c:/celesto-secure-agent")

    def is_celesto_cloud_configured(self) -> bool:
        """Check whether live Celesto Cloud credentials have been supplied."""
        return (
            bool(self.CELESTO_API_KEY)
            and self.CELESTO_API_KEY != "replace_with_your_celesto_api_key"
            and not self.CELESTO_API_KEY.startswith("replace_")
        )

    def is_llm_configured(self) -> bool:
        """Check whether live LLM credentials have been supplied."""
        return (
            bool(self.LLM_API_KEY)
            and self.LLM_API_KEY != "replace_with_your_llm_api_key"
            and not self.LLM_API_KEY.startswith("replace_")
        )


settings = Settings()
