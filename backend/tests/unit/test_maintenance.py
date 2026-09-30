from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from sqlmodel import Session

from app.tasks.maintenance import cleanup_old_speech, cleanup_old_speech_audio


def _make_obj(name: str, age_days: int) -> MagicMock:
    obj = MagicMock()
    obj.object_name = name
    obj.last_modified = datetime.now(timezone.utc) - timedelta(days=age_days)
    return obj


class TestCleanupOldSpeech:
    def test_deletes_only_expired_speech_objects(self):
        old = _make_obj("speech/room_1/audio/a.wav", 45)
        fresh = _make_obj("speech/room_1/audio/b.wav", 5)
        doc = _make_obj("documents/room_1/x.pdf", 90)

        mock_client = MagicMock()
        mock_client.list_objects.side_effect = (
            lambda bucket, prefix="", recursive=False: [
                o for o in (old, fresh, doc) if o.object_name.startswith(prefix)
            ]
        )

        with (
            patch("app.tasks.maintenance.get_minio_client", return_value=mock_client),
            patch("app.tasks.maintenance.delete_object") as mock_delete,
        ):
            db = MagicMock(spec=Session)
            assert cleanup_old_speech_audio(db, 0.0) == 1
            mock_delete.assert_called_once_with("speech/room_1/audio/a.wav")

    def test_lists_only_speech_prefix(self):
        mock_client = MagicMock()
        mock_client.list_objects.return_value = []

        with (
            patch("app.tasks.maintenance.get_minio_client", return_value=mock_client),
            patch("app.tasks.maintenance.delete_object"),
        ):
            db = MagicMock(spec=Session)
            assert cleanup_old_speech_audio(db, 0.0) == 0
            mock_client.list_objects.assert_called_once_with(
                "eroom-test", prefix="speech/", recursive=True,
            )

    def test_disabled_when_retention_zero(self):
        import app.tasks.maintenance as maintenance_mod

        fake_settings = MagicMock()
        fake_settings.speech_retention_days = 0

        with (
            patch.object(maintenance_mod, "settings", fake_settings),
            patch("app.tasks.maintenance.get_minio_client") as mock_client,
        ):
            db = MagicMock(spec=Session)
            assert cleanup_old_speech_audio(db, 0.0) == 0
            assert not mock_client.called

    def test_task_registered_with_expected_name(self):
        from app.integration.celery import celery_app

        assert "app.tasks.maintenance.cleanup_old_speech" in celery_app.tasks.keys()
        assert cleanup_old_speech is not None
