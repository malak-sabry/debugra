from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLMs
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    hackclub_api_key: str = ""
    hackclub_base_url: str = "https://ai.hackclub.com/proxy/v1"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    llm_planner: str = "claude-sonnet-4-5"
    llm_actor: str = "ollama/llama3.1:8b"
    llm_reporter: str = "claude-sonnet-4-5"

    # Database
    database_url: str = "postgresql+asyncpg://debugra:debugra@localhost:5432/debugra"
    redis_url: str = "redis://localhost:6379/0"

    # Server
    orchestrator_host: str = "0.0.0.0"
    orchestrator_port: int = 8000
    secret_key: str = "change-me-in-production"

    # Agent
    agent_step_limit: int = 40
    agent_wall_clock_seconds: int = 300
    playwright_headless: bool = True
    artifacts_dir: str = "./runs"

    # Features
    uiux_detection_enabled: bool = True
    uiux_vision_model: str = "google/gemini-2.5-flash"

    # SUTs
    lms_base_url: str = "http://localhost:3001"
    lms_api_url: str = "http://localhost:8001"
    shop_base_url: str = "http://localhost:3002"
    shop_api_url: str = "http://localhost:8002"


@lru_cache
def get_settings() -> Settings:
    return Settings()
