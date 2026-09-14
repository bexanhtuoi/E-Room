from unittest.mock import AsyncMock, Mock, patch

import pytest
from openai import APIError, APIStatusError, APITimeoutError

from app.utils.retry import MAX_ATTEMPTS, EmptyLLMResponse, aresilient, aretry, backoff_delay, is_retryable_error


def status_error(status_code: int) -> APIStatusError:
    return APIStatusError(
        "boom",
        response=Mock(status_code=status_code),
        body={},
    )


class TestBackoffDelay:
    def test_doubles_each_attempt(self):
        assert backoff_delay(2.0, 1) == 2.0
        assert backoff_delay(2.0, 2) == 4.0
        assert backoff_delay(2.0, 3) == 8.0


class TestIsRetryableError:
    def test_transient_errors_retry(self):
        assert is_retryable_error(APITimeoutError(request=Mock())) is True
        assert is_retryable_error(EmptyLLMResponse()) is True
        assert is_retryable_error(status_error(429)) is True
        assert is_retryable_error(status_error(502)) is True
        assert is_retryable_error(APIError("exhausted", request=Mock(), body={})) is True

    def test_fatal_errors_raise_immediately(self):
        assert is_retryable_error(status_error(400)) is False
        assert is_retryable_error(status_error(401)) is False
        assert is_retryable_error(ValueError("bad")) is False


class TestAretry:
    @pytest.mark.asyncio
    async def test_succeeds_after_transient_failures(self):
        calls = []

        @aretry(max_attempts=5, base_delay=0.01)
        async def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise APITimeoutError(request=Mock())
            return "ok"

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            assert await flaky() == "ok"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        calls = []

        @aretry(max_attempts=5, base_delay=0.01)
        async def always_fail():
            calls.append(1)
            raise APITimeoutError(request=Mock())

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(APITimeoutError):
                await always_fail()
        assert len(calls) == MAX_ATTEMPTS

    @pytest.mark.asyncio
    async def test_generic_api_error_retries(self):
        calls = []

        @aretry(max_attempts=5, base_delay=0.01)
        async def upstream_exhausted():
            calls.append(1)
            if len(calls) < 3:
                raise APIError("exhausted", request=Mock(), body={})
            return "recovered"

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            assert await upstream_exhausted() == "recovered"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_fatal_error_does_not_retry(self):
        calls = []

        @aretry(max_attempts=5, base_delay=0.01)
        async def fatal():
            calls.append(1)
            raise status_error(400)

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(APIStatusError):
                await fatal()
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_empty_result_retries_when_enabled(self):
        calls = []

        @aretry(max_attempts=5, base_delay=0.01, retry_on_empty=True)
        async def empty_then_ok():
            calls.append(1)
            return "" if len(calls) < 3 else "ok"

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            assert await empty_then_ok() == "ok"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_empty_result_passes_through_when_disabled(self):
        @aretry(max_attempts=5, base_delay=0.01)
        async def empty():
            return ""

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            assert await empty() == ""

    @pytest.mark.asyncio
    async def test_persistent_empty_raises_after_max_attempts(self):
        calls = []

        @aretry(max_attempts=5, base_delay=0.01, retry_on_empty=True)
        async def always_empty():
            calls.append(1)
            return "   "

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(EmptyLLMResponse):
                await always_empty()
        assert len(calls) == MAX_ATTEMPTS


class TestAresilient:
    @pytest.mark.asyncio
    async def test_retries_failed_stream_until_content(self):
        creations = []

        @aresilient(max_attempts=5, base_delay=0.01)
        async def flaky_stream():
            creations.append(1)
            if len(creations) < 3:
                raise APITimeoutError(request=Mock())
            yield {"kind": "token", "text": "hi"}

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            events = [event async for event in flaky_stream()]
        assert events == [{"kind": "token", "text": "hi"}]
        assert len(creations) == 3

    @pytest.mark.asyncio
    async def test_no_retry_after_partial_publish(self):
        creations = []

        @aresilient(max_attempts=5, base_delay=0.01)
        async def partial_then_fail():
            creations.append(1)
            yield {"kind": "token", "text": "half"}
            raise APITimeoutError(request=Mock())

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(APITimeoutError):
                [event async for event in partial_then_fail()]
        assert len(creations) == 1

    @pytest.mark.asyncio
    async def test_empty_stream_retries_then_raises(self):
        creations = []

        @aresilient(max_attempts=3, base_delay=0.01)
        async def silent_stream():
            creations.append(1)
            if False:
                yield {"kind": "token", "text": "never"}

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(EmptyLLMResponse):
                [event async for event in silent_stream()]
        assert len(creations) == 3

    @pytest.mark.asyncio
    async def test_thinking_only_stream_passes_through(self):
        creations = []

        @aresilient(max_attempts=3, base_delay=0.01)
        async def thinking_only_stream():
            creations.append(1)
            yield {"kind": "thinking", "text": "hmm"}

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            events = [event async for event in thinking_only_stream()]
        assert events == [{"kind": "thinking", "text": "hmm"}]
        assert len(creations) == 1

    @pytest.mark.asyncio
    async def test_fatal_stream_error_raises_immediately(self):
        creations = []

        @aresilient(max_attempts=5, base_delay=0.01)
        async def fatal_stream():
            creations.append(1)
            raise status_error(400)
            yield {"kind": "token", "text": "never"}

        with patch("app.utils.retry.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(APIStatusError):
                [event async for event in fatal_stream()]
        assert len(creations) == 1


class TestLlmCallTimeout:
    def test_defaults_to_120_seconds(self, monkeypatch):
        import importlib

        import app.config as config_module

        monkeypatch.delenv("LLM_CALL_TIMEOUT_SECONDS", raising=False)
        settings = importlib.reload(config_module).Settings()
        assert settings.llm_call_timeout_seconds == 120

    def test_explicit_value_is_respected(self, monkeypatch):
        import importlib

        import app.config as config_module

        monkeypatch.setenv("LLM_CALL_TIMEOUT_SECONDS", "60")
        settings = importlib.reload(config_module).Settings()
        assert settings.llm_call_timeout_seconds == 60
        monkeypatch.delenv("LLM_CALL_TIMEOUT_SECONDS", raising=False)
        importlib.reload(config_module)
