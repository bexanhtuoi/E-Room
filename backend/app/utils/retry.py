from __future__ import annotations

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


def _compute_delay(attempt: int, config: RetryConfig) -> float:
    delay = config.base_delay_seconds * (config.backoff_multiplier ** (attempt - 1))
    delay = min(delay, config.max_delay_seconds)
    if config.jitter:
        delay = delay * (0.5 + random.random())
    return delay


def sync_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay,
        retryable_exceptions=retryable,
    )

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as exc:
                    last_exception = exc
                    if attempt == config.max_attempts:
                        logger.error(
                            "Sync retry exhausted function=%s attempts=%d",
                            func.__name__,
                            attempt,
                        )
                        raise
                    delay = _compute_delay(attempt, config)
                    logger.warning(
                        "Sync retry attempt %d/%d function=%s delay=%0.2fs error=%s",
                        attempt,
                        config.max_attempts,
                        func.__name__,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay,
        retryable_exceptions=retryable,
    )

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as exc:
                    last_exception = exc
                    if attempt == config.max_attempts:
                        logger.error(
                            "Async retry exhausted function=%s attempts=%d",
                            func.__name__,
                            attempt,
                        )
                        raise
                    delay = _compute_delay(attempt, config)
                    logger.warning(
                        "Async retry attempt %d/%d function=%s delay=%0.2fs error=%s",
                        attempt,
                        config.max_attempts,
                        func.__name__,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
