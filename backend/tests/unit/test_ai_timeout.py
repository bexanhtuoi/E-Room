import importlib

import app.config as config_module


def reload_settings(monkeypatch, env):
    for key in ("AI_TIMEOUT_SECONDS", "AI_SOFT_TIMEOUT_SECONDS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(config_module).Settings()


class TestAiTimeout:
    def test_soft_defaults_to_hard_minus_60(self, monkeypatch):
        settings = reload_settings(monkeypatch, {"AI_TIMEOUT_SECONDS": "900"})
        assert settings.ai_timeout_seconds == 900
        assert settings.ai_soft_timeout_seconds == 840

    def test_explicit_soft_is_respected(self, monkeypatch):
        settings = reload_settings(
            monkeypatch,
            {"AI_TIMEOUT_SECONDS": "900", "AI_SOFT_TIMEOUT_SECONDS": "600"},
        )
        assert settings.ai_soft_timeout_seconds == 600

    def test_soft_never_exceeds_hard(self, monkeypatch):
        settings = reload_settings(
            monkeypatch,
            {"AI_TIMEOUT_SECONDS": "300", "AI_SOFT_TIMEOUT_SECONDS": "900"},
        )
        assert settings.ai_soft_timeout_seconds <= settings.ai_timeout_seconds

    def test_celery_soft_limit_below_hard_limit(self):
        from app.integration.celery import celery_app

        assert celery_app.conf.task_soft_time_limit <= celery_app.conf.task_time_limit
