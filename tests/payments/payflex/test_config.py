"""
Tests for Payflex configuration: env variable resolution, sandbox/production toggle,
and validation.
"""
import pytest
from app.payments.payflex.config import PayflexSettings


class TestPayflexConfig:
    def test_sandbox_urls_resolved(self):
        settings = PayflexSettings(
            payflex_mode="sandbox",
            payflex_client_id="test",
            payflex_client_secret="secret",
            payflex_redirect_url="http://localhost:3000/return",
            payflex_callback_url="http://localhost:8000/webhook",
        )
        assert "sandbox" in settings.payflex_auth_url
        assert "sandbox" in settings.payflex_api_url
        assert "sandbox" in settings.payflex_audience

    def test_production_urls_resolved(self):
        settings = PayflexSettings(
            payflex_mode="production",
            payflex_client_id="test",
            payflex_client_secret="secret",
            payflex_redirect_url="https://elitetcg.co.za/return",
            payflex_callback_url="https://api.elitetcg.co.za/webhook",
        )
        assert "sandbox" not in settings.payflex_auth_url
        assert "sandbox" not in settings.payflex_api_url
        assert settings.payflex_auth_url == "https://auth.payflex.co.za/auth/merchant"

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="sandbox.*production"):
            PayflexSettings(payflex_mode="invalid")

    def test_is_configured_true(self):
        settings = PayflexSettings(
            payflex_mode="sandbox",
            payflex_client_id="test",
            payflex_client_secret="secret",
            payflex_redirect_url="http://localhost/return",
            payflex_callback_url="http://localhost/webhook",
        )
        assert settings.is_configured is True

    def test_is_configured_false_missing_client_id(self):
        settings = PayflexSettings(
            payflex_mode="sandbox",
            payflex_client_id="",
            payflex_client_secret="secret",
            payflex_redirect_url="http://localhost/return",
            payflex_callback_url="http://localhost/webhook",
        )
        assert settings.is_configured is False

    def test_is_configured_false_missing_secret(self):
        settings = PayflexSettings(
            payflex_mode="sandbox",
            payflex_client_id="test",
            payflex_client_secret="",
            payflex_redirect_url="http://localhost/return",
            payflex_callback_url="http://localhost/webhook",
        )
        assert settings.is_configured is False

    def test_is_sandbox_property(self):
        settings = PayflexSettings(payflex_mode="sandbox")
        assert settings.is_sandbox is True

        settings2 = PayflexSettings(payflex_mode="production")
        assert settings2.is_sandbox is False

    def test_custom_url_override(self):
        settings = PayflexSettings(
            payflex_mode="sandbox",
            payflex_api_url="https://custom-api.example.com",
        )
        assert settings.payflex_api_url == "https://custom-api.example.com"
        # Other URLs should still be sandbox defaults
        assert "sandbox" in settings.payflex_auth_url
