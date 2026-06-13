from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# The shipped default secret. Acceptable for local development only; the
# app refuses to start in production while this is still in use.
INSECURE_JWT_DEFAULT = "change-this-in-production"
MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    app_name: str = "Automotive Insurance Claim Workflow Orchestration System"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"
    document_storage_path: str = "storage/documents"
    max_document_size_bytes: int = 10 * 1024 * 1024
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    jwt_secret_key: str = INSECURE_JWT_DEFAULT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 120
    database_url: str = "sqlite:///./claims_local.db"
    amqp_url: str | None = None
    rate_limit_default: int = 200
    rate_limit_auth: int = 20
    rate_limit_window_seconds: int = 60

    # Comma-separated allowed CORS origins. "*" is permitted only outside
    # production; production must name explicit origins.
    cors_allow_origins: str = "*"

    # Optional bootstrap administrator, created on startup if it does not
    # exist. This is how the first admin is provisioned now that public
    # registration can no longer self-assign the admin role.
    bootstrap_admin_username: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


def validate_security(settings: "Settings") -> list[str]:
    """Return a list of security misconfigurations that must block startup
    in production. Empty list means the configuration is acceptable."""
    problems: list[str] = []
    if not settings.is_production:
        return problems

    if (
        settings.jwt_secret_key == INSECURE_JWT_DEFAULT
        or len(settings.jwt_secret_key) < MIN_PRODUCTION_SECRET_LENGTH
    ):
        problems.append(
            "JWT_SECRET_KEY must be overridden with a strong value "
            f"(>= {MIN_PRODUCTION_SECRET_LENGTH} chars) in production"
        )
    if "*" in settings.cors_origins:
        problems.append(
            "CORS_ALLOW_ORIGINS must list explicit origins in production, not '*'"
        )
    if settings.database_url.startswith("sqlite"):
        problems.append("A production database must be configured (not SQLite)")
    return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
