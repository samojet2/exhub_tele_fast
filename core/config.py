from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -----------------------------
    # Application
    # -----------------------------

    app_name: str = "Telegram Service"
    debug: bool = False

    # -----------------------------
    # Telegram
    # -----------------------------

    telegram_main_bot_token: str | None = None
    telegram_proxy_url: str | None = None

    # -----------------------------
    # Queue
    # -----------------------------

    queue_max_size: int = 1000
    worker_count: int = 1

    # -----------------------------
    # Settings
    # -----------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()