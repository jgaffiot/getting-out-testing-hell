"""Typed settings, replacing the scattered ``os.environ.get`` calls in ``app.config``.

Values are resolved from, in order of precedence: CLI arguments, environment
variables, then a ``.env`` file - see ``pydantic-settings``' built-in sources.
This lets ``PaymentClient``/``EmailClient`` be reconfigured for local dev
(``.env``), CI (env vars) or a one-off run (``--payment-api-key=...``)
without touching code.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for the payment and email clients."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        cli_parse_args=True,
        cli_ignore_unknown_args=True,
        cli_kebab_case=True,
        extra="ignore",
    )

    payment_api_url: str = "https://api.fakepay.io/v1"
    payment_api_key: str = "sk_test_changeme"

    email_smtp_host: str = "localhost"
    email_smtp_port: int = 1025
    email_from: str = "shop@bookstore.local"


@lru_cache
def get_settings() -> Settings:
    """Build (and cache) the process-wide Settings instance.

    Cached so CLI args/`.env` are only parsed once per process rather than on
    every request.
    """
    return Settings()
