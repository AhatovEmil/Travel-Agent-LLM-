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

    # Бесплатные полные генерации плана (POST /run) на календарный месяц UTC
    free_generations_per_month: int = 5
    # Fallback-ссылка (бот или поддержка), если Tribute не настроен
    support_telegram: str = "https://t.me/"
    # Секрет для POST /api/admin/credits (пусто = эндпоинт выключен)
    admin_credit_token: str = ""

    # Tribute digital products + webhook
    tribute_api_key: str = ""
    tribute_product_10: str = ""
    tribute_product_30: str = ""
    tribute_product_100: str = ""
    tribute_link_10: str = ""
    tribute_link_30: str = ""
    tribute_link_100: str = ""

    # Telegram bot: шлёт ссылки на оплату Tribute; Login Widget / WebApp link
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    def tribute_product_map(self) -> dict[str, int]:
        """product_id (str) -> credits."""
        mapping: dict[str, int] = {}
        for pid, credits in (
            (self.tribute_product_10, 10),
            (self.tribute_product_30, 30),
            (self.tribute_product_100, 100),
        ):
            key = str(pid or "").strip()
            if key:
                mapping[key] = credits
        return mapping

    @property
    def generation_packages(self) -> list[dict]:
        bot = (self.telegram_bot_username or "").strip().lstrip("@")
        bot_base = f"https://t.me/{bot}" if bot else (self.support_telegram or "https://t.me/").rstrip("/")

        def pack(pid: str, gens: int, price: int, label: str, link: str, start: str) -> dict:
            tribute_url = (link or "").strip()
            # Кнопка «Купить» ведёт в нашего бота с deep-link; бот ответит ссылкой Tribute
            buy_url = f"{bot_base}?start={start}" if bot else (tribute_url or bot_base)
            return {
                "id": pid,
                "generations": gens,
                "price_rub": price,
                "label": label,
                "tribute_url": tribute_url,
                "buy_url": buy_url,
            }

        return [
            pack(
                "pack10",
                10,
                299,
                "10 генераций",
                self.tribute_link_10,
                "buy10",
            ),
            pack(
                "pack30",
                30,
                699,
                "30 генераций",
                self.tribute_link_30,
                "buy30",
            ),
            pack(
                "pack100",
                100,
                1990,
                "100 генераций",
                self.tribute_link_100,
                "buy100",
            ),
        ]

    def bot_deep_link(self, start: str = "buy") -> str:
        bot = (self.telegram_bot_username or "").strip().lstrip("@")
        if not bot:
            return (self.support_telegram or "https://t.me/").strip()
        return f"https://t.me/{bot}?start={start}"

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
