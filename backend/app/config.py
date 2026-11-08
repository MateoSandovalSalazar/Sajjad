from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRETS = {"change-me", "changeme", "secret", ""}


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
    # Hosts aceptados por TrustedHostMiddleware en producción.
    allowed_hosts: str = "sajjad.app,*.sajjad.app"

    # Database
    database_url: str = (
        "postgresql+asyncpg://sajjad:sajjad@localhost:5432/sajjad_db"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate limiting. Se desactiva sólo en tests, donde los mismos
    # endpoints se llaman decenas de veces seguidas a propósito.
    rate_limit_enabled: bool = True

    # Observabilidad. Sin DSN, Sentry queda desactivado por completo
    # y no hace falta instalar la dependencia.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    release_version: str = "dev"

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

    # Billing / Mercado Pago
    #
    # billing_enabled es el interruptor maestro del cobro. Mientras
    # esté en false, /billing/checkout y /billing/cancel responden
    # 503 y el webhook no se monta: el producto funciona completo
    # sin pasarela de pagos. Activar MercadoPago = poner las
    # credenciales y cambiar este flag a true. Nada más.
    billing_enabled: bool = False

    # Días de prueba con capacidades de Professional, otorgados al
    # verificar el email. 0 desactiva el trial.
    trial_days: int = 14

    mp_access_token: str = ""
    mp_public_key: str = ""
    mp_webhook_secret: str = ""

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
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        """
        Falla al arrancar si producción está mal configurada.

        Preferimos que el contenedor no levante a que levante con
        JWT forjables o pagos a medio conectar: un fallo ruidoso al
        desplegar es barato, uno silencioso en producción no.
        """
        if not self.is_production:
            return self

        errors: list[str] = []

        if self.api_secret_key.strip().lower() in _INSECURE_SECRETS:
            errors.append(
                "API_SECRET_KEY tiene el valor por defecto. "
                "Genera uno con: openssl rand -hex 32"
            )
        elif len(self.api_secret_key) < 32:
            errors.append(
                "API_SECRET_KEY es demasiado corta "
                "(mínimo 32 caracteres)."
            )

        if any(o == "*" for o in self.cors_origins):
            errors.append(
                "ALLOWED_ORIGINS no puede ser '*' en producción."
            )

        if self.billing_enabled:
            if not self.mp_access_token:
                errors.append(
                    "BILLING_ENABLED=true pero falta MP_ACCESS_TOKEN."
                )
            if not self.mp_webhook_secret:
                errors.append(
                    "BILLING_ENABLED=true pero falta MP_WEBHOOK_SECRET "
                    "(sin él no se puede validar la firma del webhook)."
                )

        if errors:
            raise ValueError(
                "Configuración de producción inválida:\n  - "
                + "\n  - ".join(errors)
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
