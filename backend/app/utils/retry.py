import asyncio
import functools
from collections.abc import AsyncIterable
from typing import Any, Awaitable, Callable, Tuple, Type

from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError, InternalServerError, RateLimitError

from app.log import get_logger

log = get_logger("app.utils.retry", level="INFO")

MAX_ATTEMPTS = 5

RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}

RetriableError: Tuple[Type[BaseException], ...] = (
    APIError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
    asyncio.TimeoutError,
)


class EmptyLLMResponse(Exception):
    pass


def is_empty_text(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    return False


def is_retryable_error(error: BaseException) -> bool:
    if isinstance(error, EmptyLLMResponse):
        return True

    if isinstance(error, APIStatusError):
        return error.status_code is None or error.status_code in RETRYABLE_STATUS_CODES

    return isinstance(error, RetriableError)


def backoff_delay(base_delay: float, attempt: int) -> float:
    return base_delay * (2 ** (attempt - 1))


def is_content_event(event: Any) -> bool:
    if isinstance(event, str):
        return bool(event.strip())

    if isinstance(event, dict):
        return event.get("kind", "token") != "thinking" and bool(event.get("text"))

    return False


def aresilient(
    max_attempts: int = MAX_ATTEMPTS,
    base_delay: float = 2.0,
) -> Callable:
    def decorator(func: Callable[..., AsyncIterable[Any]]) -> Callable[..., AsyncIterable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> AsyncIterable[Any]:
            attempt = 0

            while True:
                attempt += 1
                seen_any = False
                published = False

                try:
                    async for event in func(*args, **kwargs):
                        seen_any = True
                        if is_content_event(event):
                            published = True
                        yield event

                    if published or seen_any:
                        return

                    raise EmptyLLMResponse("LLM stream ended with no content")
                except Exception as error:
                    if published or not is_retryable_error(error) or attempt >= max_attempts:
                        raise

                    delay = backoff_delay(base_delay, attempt)

                    log.warning(
                        "LLM stream failed, retrying | func=%s attempt=%s/%s delay=%.1fs error=%s",
                        func.__name__,
                        attempt,
                        max_attempts,
                        delay,
                        error,
                    )

                    await asyncio.sleep(delay)

        return wrapper

    return decorator


def aretry(
    max_attempts: int = MAX_ATTEMPTS,
    base_delay: float = 2.0,
    retry_on_empty: bool = False,
) -> Callable:
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0

            while True:
                attempt += 1

                try:
                    result = await func(*args, **kwargs)

                    if retry_on_empty and is_empty_text(result):
                        raise EmptyLLMResponse("LLM returned empty response")

                    return result
                except Exception as error:
                    if not is_retryable_error(error) or attempt >= max_attempts:
                        raise

                    delay = backoff_delay(base_delay, attempt)

                    log.warning(
                        "LLM call failed, retrying | func=%s attempt=%s/%s delay=%.1fs error=%s",
                        func.__name__,
                        attempt,
                        max_attempts,
                        delay,
                        error,
                    )

                    await asyncio.sleep(delay)

        return wrapper

    return decorator
