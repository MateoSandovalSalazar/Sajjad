from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API
    api_env: str = "development"
    api_secret_key: str = "change-me"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"

    # Database
    database_url: str = (
        "postgresql+asyncpg://sajjad:sajjad@localhost:5432/sajjad_db"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@sajjad.app"
    smtp_tls: bool = False        # SSL on connect (port 465)
    smtp_starttls: bool = True    # STARTTLS upgrade (port 587)
    email_from_name: str = "Sajjad EASM"

    # Mercado Pago
    mp_access_token: str = ""
    mp_public_key: str = ""
    mp_webhook_secret: str = ""
    mp_plan_starter_id: str = ""
    mp_plan_professional_id: str = ""
    mp_plan_agency_id: str = ""

    # Scanner
    scan_timeout: int = 300
    nuclei_rate_limit: int = 150
    pdf_storage_path: str = "/tmp/sajjad/reports"

    # OSINT
    hibp_api_key: str = ""
    github_token: str = ""
    shodan_api_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.api_env == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
