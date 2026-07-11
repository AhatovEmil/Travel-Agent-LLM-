from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_JWT_DEFAULT = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Travel Agent"
    # development | production — в production жёсткие проверки секретов/CORS
    environment: str = "development"
    database_url: str = "sqlite:///./travel.db"
    jwt_secret: str = INSECURE_JWT_DEFAULT
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    # DeepSeek (обязателен для планирования поездок)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_model_fallbacks: str = "deepseek-reasoner"

    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost,https://localhost"
    )

    # Лимит LLM-операций на пользователя в час (run/chat/ask/adjust/…)
    llm_rate_limit_per_hour: int = 20
    # Auth: запросов с одного IP в минуту (login + register)
    auth_rate_limit_per_minute: int = 10
    # Share: GET/POST с одного IP в минуту
    share_rate_limit_per_minute: int = 60

    # False — закрыть публичную регистрацию (только логин)
    registration_enabled: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    def validate_for_runtime(self) -> None:
        """Падаем при небезопасной конфигурации в production."""
        if not self.is_production:
            return
        secret = (self.jwt_secret or "").strip()
        if secret == INSECURE_JWT_DEFAULT or len(secret) < 32:
            raise RuntimeError(
                "JWT_SECRET must be a strong random value (>=32 chars), "
                "not the default. Generate with: openssl rand -hex 32"
            )
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if not origins or any(o == "*" for o in origins):
            raise RuntimeError(
                "CORS_ORIGINS must list explicit origins in production "
                "(e.g. https://ai-travel-assistant.ru), not *"
            )


settings = Settings()
settings.validate_for_runtime()
