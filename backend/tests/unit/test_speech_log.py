import json
from unittest.mock import MagicMock, patch

import numpy as np

from app.ai.pronunciation import heuristic_score, score_pronunciation
from app.ai.speech_log import (
    append_utterance,
    attach_feedback,
    attach_pronunciation,
    get_room_transcript_for_summary,
    read_user_log,
    update_corrected_text,
)


def _audio():
    return np.zeros(16000, dtype=np.int16)


class TestSpeechLog:
    def test_append_read_update_cycle(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEECH_LOG_DIR", str(tmp_path))
        # import lại để nhận env mới (get_speech_log_dir đọc settings mỗi lần gọi)
        import app.config as cfg

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        monkeypatch.setattr(cfg.settings, "speech_log_save_audio", True, raising=False)

        entry = append_utterance(
            room_id=999,
            user_id=7,
            user_name="An",
            message_id=123,
            text="hello everyone",
            language="en",
            duration=1.5,
            confidence=0.9,
            avg_logprob=-0.2,
            words=[{"word": "hello", "start": 0.0, "end": 0.5, "probability": 0.9}],
            provider="whisper_server_test",
            audio_data=_audio(),
        )
        assert entry["corrected_text"] == "hello everyone"
        assert entry["audio_file"] is not None
        assert entry["audio_file"].endswith(".wav")

        logs = read_user_log(999, 7)
        assert len(logs) == 1
        assert logs[0]["message_id"] == 123

        updated = update_corrected_text(999, 7, 123, "hello everybody")
        assert updated is not None
        assert updated["corrected_text"] == "hello everybody"
        assert updated["edited_at"] is not None

        logs2 = read_user_log(999, 7)
        assert logs2[0]["corrected_text"] == "hello everybody"

        score = {"score": 88.5, "method": "heuristic-v1", "wav2vec_ready": False}
        attached = attach_pronunciation(999, 7, 123, score)
        assert attached is not None
        assert attached["pronunciation"]["score"] == 88.5

    def test_summary_prefers_corrected_text(self, tmp_path, monkeypatch):
        import app.config as cfg

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        monkeypatch.setattr(cfg.settings, "speech_log_save_audio", False, raising=False)

        append_utterance(room_id=1001, user_id=1, user_name="A", message_id=1, text="raw one", audio_data=None)
        append_utterance(room_id=1001, user_id=2, user_name="B", message_id=2, text="raw two", audio_data=None)
        update_corrected_text(1001, 1, 1, "fixed one")

        summary = get_room_transcript_for_summary(1001)
        by_id = {s["message_id"]: s for s in summary}
        assert by_id[1]["text"] == "fixed one"
        assert by_id[1]["raw_text"] == "raw one"
        assert by_id[2]["text"] == "raw two"

    def test_update_missing_returns_none(self, tmp_path, monkeypatch):
        import app.config as cfg

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        monkeypatch.setattr(cfg.settings, "speech_log_save_audio", False, raising=False)
        assert update_corrected_text(5555, 1, 999999, "x") is None

    def test_raw_edit_rescore_flow(self, tmp_path, monkeypatch):
        """whisper lưu raw (chưa chấm) -> user sửa -> chấm -> sửa nữa thì mất điểm cũ."""
        import app.config as cfg

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        monkeypatch.setattr(cfg.settings, "speech_log_save_audio", False, raising=False)

        # 1. whisper thu vào -> raw, pronunciation=None
        entry = append_utterance(
            room_id=2002, user_id=3, user_name="C", message_id=7,
            text="you are using a satellite", audio_data=None,
        )
        assert entry["pronunciation"] is None

        # 2. user review + sửa chính tả
        updated = update_corrected_text(2002, 3, 7, "you're using a satellite")
        assert updated["corrected_text"] == "you're using a satellite"
        assert updated["pronunciation"] is None

        # 3. chấm trên bản đã sửa
        score = score_pronunciation(
            audio_path=None, reference_text=updated["corrected_text"],
            confidence=0.95, avg_logprob=-0.1, duration=6.54,
            words=[{}, {}, {}, {}],
        )
        score["scored_text"] = updated["corrected_text"]
        attached = attach_pronunciation(2002, 3, 7, score)
        assert attached["pronunciation"]["scored_text"] == "you're using a satellite"

        # 4. sửa tiếp sau khi đã có điểm -> điểm cũ bị reset, bắt chấm lại
        updated2 = update_corrected_text(2002, 3, 7, "you're using a satellite!")
        assert updated2["pronunciation"] is None
        assert updated2["edited_at"] is not None

        # 5. PATCH cùng nội dung (không đổi) -> giữ điểm
        attach_pronunciation(2002, 3, 7, score)
        updated3 = update_corrected_text(2002, 3, 7, "you're using a satellite!")
        assert updated3["pronunciation"]["scored_text"] == "you're using a satellite"

    def test_feedback_flow_and_reset_on_edit(self, tmp_path, monkeypatch):
        """chấm -> gắn feedback -> sửa text thì cả điểm + feedback đều reset."""
        import app.config as cfg

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        monkeypatch.setattr(cfg.settings, "speech_log_save_audio", False, raising=False)

        append_utterance(
            room_id=3003, user_id=5, user_name="D", message_id=9,
            text="hello world", audio_data=None,
        )
        score = score_pronunciation(
            audio_path=None, reference_text="hello world",
            confidence=0.9, avg_logprob=-0.2, duration=1.0, words=[{}, {}],
        )
        attach_pronunciation(3003, 5, 9, score)
        fb = {"feedback_raw": "Good job.", "model": "test-model"}
        attached = attach_feedback(3003, 5, 9, fb)
        assert attached["feedback"]["model"] == "test-model"

        # summary mang cả điểm + feedback
        summary = get_room_transcript_for_summary(3003)
        assert summary[0]["pronunciation"]["score"] == score["score"]
        assert summary[0]["feedback"]["model"] == "test-model"

        # sửa text -> reset cả hai, bắt chấm + xin feedback lại
        updated = update_corrected_text(3003, 5, 9, "hello brave world")
        assert updated["pronunciation"] is None
        assert updated["feedback"] is None

        assert attach_feedback(3003, 5, 999999, fb) is None


class TestFindAttempt:
    def _make_attempt(self, base, room_id, att_id, user_id, msgs):
        import json as _json
        d = base / f"room_{room_id}" / "attempts" / att_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "raw.wav").write_bytes(b"RIFF" + b"\x00" * 100)
        meta = {
            "attempt_id": att_id, "user_id": user_id, "user_identity": str(user_id),
            "utterances": [
                {"index": i, "message_id": m, "start_sec": float(i), "end_sec": float(i + 1)}
                for i, m in enumerate(msgs)
            ],
        }
        (d / "metadata.json").write_text(_json.dumps(meta), encoding="utf-8")

    def test_found_and_scoped_by_user(self, tmp_path, monkeypatch):
        import app.config as cfg
        from app.ai.raw_recorder import find_attempt_by_message

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        self._make_attempt(tmp_path, 11, "att1", 3, [71, 72])

        got = find_attempt_by_message(11, 3, 72)
        assert got is not None and got["attempt_id"] == "att1"
        assert got["raw_path"] is not None and got["message_ids"] == [71, 72]

        assert find_attempt_by_message(11, 999, 72) is None  # sai user
        assert find_attempt_by_message(11, 3, 12345) is None  # sai message
        assert find_attempt_by_message(99, 3, 72) is None  # sai room

    def test_missing_raw_wav_gives_none_path(self, tmp_path, monkeypatch):
        import app.config as cfg
        from app.ai.raw_recorder import find_attempt_by_message

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        self._make_attempt(tmp_path, 12, "att2", 4, [81])
        import pathlib as _pl
        _pl.Path(tmp_path, "room_12", "attempts", "att2", "raw.wav").unlink()
        got = find_attempt_by_message(12, 4, 81)
        assert got is not None and got["raw_path"] is None  # router rớt về wav VAD


class TestPronunciation:
    def test_heuristic_bounds(self):
        good = heuristic_score(confidence=0.95, avg_logprob=-0.1, duration=2.0, words_count=5)
        bad = heuristic_score(confidence=0.2, avg_logprob=-1.8, duration=0.5, words_count=1)
        assert 0 <= bad["score"] <= good["score"] <= 100
        assert good["method"] == "heuristic-v1"
        assert good["wav2vec_ready"] is False

    def test_score_pronunciation_fallback_without_audio(self):
        result = score_pronunciation(
            audio_path=None, reference_text="hello", confidence=0.9, avg_logprob=-0.2, duration=1.0, words=[{}, {}]
        )
        assert 0 <= result["score"] <= 100


class TestWhisperServerProvider:
    def test_success_parses_verbose_json(self):
        import app.ai.stt as stt_module

        audio = np.zeros(16000, dtype=np.int16)
        payload = {
            "text": "hello world",
            "language": "en",
            "duration": 1.0,
            "segments": [{"avg_logprob": -0.2, "words": [{"word": "hello", "start": 0.0, "end": 0.5}]}],
        }
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = payload

        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
            result = stt_module.transcribe_whisper_server(audio, language="en")

        assert result is not None
        assert result["text"] == "hello world"
        assert result["provider"].startswith("whisper_server_")
        assert len(result["words"]) == 1

    def test_failure_returns_none_no_local_fallback(self):
        # Local model đã xóa — server down thì trả None, worker bỏ qua utterance.
        import app.ai.stt as stt_module

        audio = np.zeros(16000, dtype=np.int16)
        with patch("httpx.Client", side_effect=RuntimeError("server down")):
            assert stt_module.transcribe_whisper_server(audio) is None

    def test_dispatcher_keeps_language_for_server(self):
        import app.ai.stt as stt_module

        audio = np.zeros(16000, dtype=np.int16)
        mock_server = MagicMock(return_value={"text": "ok"})
        # Registry giữ reference gốc lúc import nên phải patch trong dict.
        with patch.dict(stt_module.STT_PROVIDERS, {"whisper_server": mock_server}):
            stt_module.transcribe_audio(audio, provider="whisper_server", language="vi")
            _, kwargs = mock_server.call_args
            assert kwargs.get("language") == "vi"


class TestSttServerUrlOverride:
    def test_redis_override_wins_over_env(self):
        import app.ai.stt as stt_module

        stt_module._STT_URL_CACHE.update({"value": None, "expires": 0.0})
        with patch("app.integration.redis.get", return_value="http://100.105.201.65:8001/v1/"):
            assert stt_module.get_stt_server_url_override() == "http://100.105.201.65:8001/v1"

    def test_empty_redis_falls_back_to_env(self):
        import app.ai.stt as stt_module

        stt_module._STT_URL_CACHE.update({"value": None, "expires": 0.0})
        with patch("app.integration.redis.get", return_value=None):
            assert stt_module.get_stt_server_url_override() is None

    def test_redis_error_fail_open(self):
        import app.ai.stt as stt_module

        stt_module._STT_URL_CACHE.update({"value": None, "expires": 0.0})
        with patch("app.integration.redis.get", side_effect=RuntimeError("down")):
            assert stt_module.get_stt_server_url_override() is None
