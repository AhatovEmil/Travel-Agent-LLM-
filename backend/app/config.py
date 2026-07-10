from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Travel Agent"
    database_url: str = "sqlite:///./travel.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    # DeepSeek (обязателен для планирования поездок)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_model_fallbacks: str = "deepseek-reasoner"

    cors_origins: str = "*"

    # Лимит LLM-операций на пользователя в час (run/chat/ask/adjust/…)
    llm_rate_limit_per_hour: int = 20


settings = Settings()
