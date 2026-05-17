from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anthropic
    anthropic_api_key: str = Field(..., description="Anthropic API key")

    # LangSmith
    langchain_api_key: str = Field(default="", description="LangSmith API key")
    langchain_tracing_v2: bool = Field(default=False)
    langchain_project: str = Field(default="ai-outreach-agent")

    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")

    # Email
    resend_api_key: str = Field(..., description="Resend API key")
    outreach_from_email: str = Field(..., description="Dedicated outreach domain email")
    outreach_from_name: str = Field(default="Zehir")

    # Notifications
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # Sourcing
    google_places_api_key: str = Field(default="", description="Google Places API key")
    tavily_api_key: str = Field(default="", description="Tavily search API key")

    # Operational controls
    environment: str = Field(default="development")
    max_emails_per_day: int = Field(default=30)
    approval_required: bool = Field(default=True)
    kill_switch: bool = Field(default=False, description="If True, all sends are blocked")

    # LLM model selection
    llm_reasoning_model: str = Field(default="claude-sonnet-4-5")
    llm_cheap_model: str = Field(default="claude-haiku-4-5-20251001")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()  # type: ignore[call-arg]
