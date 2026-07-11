"""Проверки production-конфига и CORS."""

import pytest

from app.config import INSECURE_JWT_DEFAULT, Settings


def test_production_rejects_default_jwt():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        Settings(
            environment="production",
            jwt_secret=INSECURE_JWT_DEFAULT,
            cors_origins="https://example.com",
        ).validate_for_runtime()


def test_production_rejects_short_jwt():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        Settings(
            environment="production",
            jwt_secret="too-short",
            cors_origins="https://example.com",
        ).validate_for_runtime()


def test_production_rejects_wildcard_cors():
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        Settings(
            environment="production",
            jwt_secret="a" * 32,
            cors_origins="*",
        ).validate_for_runtime()


def test_production_ok_with_strong_secret():
    Settings(
        environment="production",
        jwt_secret="a" * 32,
        cors_origins="https://ai-travel-assistant.ru",
    ).validate_for_runtime()


def test_development_allows_defaults():
    Settings(
        environment="development",
        jwt_secret=INSECURE_JWT_DEFAULT,
        cors_origins="*",
    ).validate_for_runtime()
