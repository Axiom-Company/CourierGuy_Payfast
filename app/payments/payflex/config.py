"""
Payflex environment-aware configuration.

Resolves sandbox vs production URLs automatically from PAYFLEX_MODE env var.
Validates all required credentials on construction — if any are missing,
the Payflex payment option should be disabled (not crash the app).
"""
from __future__ import annotations

import logging
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from functools import lru_cache

logger = logging.getLogger(__name__)

_ENVS = {
    "sandbox": {
        "auth_url": "https://auth.sandbox.payflex.co.za/auth/merchant",
        "api_url": "https://api.sandbox.payflex.co.za",
        "checkout_url": "https://checkout.sandbox.payflex.co.za",
        "audience": "https://auth-sandbox.payflex.co.za",
    },
    "production": {
        "auth_url": "https://auth.payflex.co.za/auth/merchant",
        "api_url": "https://api.payflex.co.za",
        "checkout_url": "https://checkout.payflex.co.za",
        "audience": "https://auth-production.payflex.co.za",
    },
}


class PayflexSettings(BaseSettings):
    """Payflex configuration loaded from environment variables."""

    payflex_mode: str = "sandbox"
    payflex_client_id: str = ""
    payflex_client_secret: str = ""
    payflex_redirect_url: str = ""
    payflex_callback_url: str = ""

    # Optional overrides (resolved from mode if not set)
    payflex_auth_url: str = ""
    payflex_api_url: str = ""
    payflex_checkout_url: str = ""
    payflex_audience: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @field_validator("payflex_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("sandbox", "production"):
            raise ValueError(f"PAYFLEX_MODE must be 'sandbox' or 'production', got '{v}'")
        return v

    @model_validator(mode="after")
    def resolve_urls(self) -> "PayflexSettings":
        """Fill in auth/api/checkout/audience URLs from mode if not explicitly set."""
        env = _ENVS[self.payflex_mode]
        if not self.payflex_auth_url:
            self.payflex_auth_url = env["auth_url"]
        if not self.payflex_api_url:
            self.payflex_api_url = env["api_url"]
        if not self.payflex_checkout_url:
            self.payflex_checkout_url = env["checkout_url"]
        if not self.payflex_audience:
            self.payflex_audience = env["audience"]
        return self

    @property
    def is_configured(self) -> bool:
        """True if all required credentials are present."""
        return bool(
            self.payflex_client_id
            and self.payflex_client_secret
            and self.payflex_redirect_url
            and self.payflex_callback_url
        )

    @property
    def is_sandbox(self) -> bool:
        return self.payflex_mode == "sandbox"


@lru_cache()
def get_payflex_settings() -> PayflexSettings:
    """Singleton access to Payflex settings. Logs a warning if not configured."""
    settings = PayflexSettings()
    if not settings.is_configured:
        logger.warning(
            "Payflex credentials incomplete — Payflex payment option will be disabled. "
            "Set PAYFLEX_CLIENT_ID, PAYFLEX_CLIENT_SECRET, PAYFLEX_REDIRECT_URL, PAYFLEX_CALLBACK_URL."
        )
    return settings
