from __future__ import annotations

"""Reusable CRUD operations for infrastructure services (Redis, MinIO, etc.).

These classes are intentionally framework-agnostic — they accept their client
as a constructor dependency so they can be re-used anywhere without importing
FastAPI or Celery specifics.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

import redis
from minio import Minio


# ---------------------------------------------------------------------------
#  Redis CRUD — typed key-value store with optional serialisation
# ---------------------------------------------------------------------------

class RedisCRUD:
    """Generic key-value operations over a Redis client.

    Usage::

        redis_crud = RedisCRUD(redis_client)
        redis_crud.set_json("user:1", {"name": "Alice"})
        data = redis_crud.get_json("user:1")
    """

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    # -- raw string ops ---------------------------------------------------

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        return self._client.set(key, value, ex=ttl)

    def delete(self, *keys: str) -> int:
        return self._client.delete(*keys)

    def exists(self, *keys: str) -> int:
        return self._client.exists(*keys)

    # -- JSON helpers -----------------------------------------------------

    def get_json(self, key: str) -> Optional[Any]:
        raw = self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        return self._client.set(key, json.dumps(value, default=str), ex=ttl)

    # -- hash ops ---------------------------------------------------------

    def hget(self, name: str, key: str) -> Optional[str]:
        return self._client.hget(name, key)

    def hset(self, name: str, key: str, value: str) -> int:
        return self._client.hset(name, key, value)

    def hgetall(self, name: str) -> dict[str, str]:
        return self._client.hgetall(name)

    # -- set ops ----------------------------------------------------------

    def sadd(self, name: str, *values: str) -> int:
        return self._client.sadd(name, *values)

    def smembers(self, name: str) -> set[str]:
        return self._client.smembers(name)

    def srem(self, name: str, *values: str) -> int:
        return self._client.srem(name, *values)

    # -- pub/sub ----------------------------------------------------------

    def publish(self, channel: str, message: Any) -> int:
        payload = message if isinstance(message, (str, bytes)) else json.dumps(message, default=str)
        return self._client.publish(channel, payload)

    # -- utility ----------------------------------------------------------

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    def keys(self, pattern: str = "*") -> list[str]:
        return self._client.keys(pattern)


# ---------------------------------------------------------------------------
#  MinIO CRUD — object storage operations
# ---------------------------------------------------------------------------

class MinioCRUD:
    """High-level object-storage operations for a MinIO bucket.

    Usage::

        minio_crud = MinioCRUD(minio_client, bucket="my-bucket")
        minio_crud.ensure_bucket()
        minio_crud.put_object("reports/2025.pdf", b"...", content_type="application/pdf")
        data = minio_crud.get_object("reports/2025.pdf")
    """

    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    # -- bucket -----------------------------------------------------------

    def ensure_bucket(self) -> None:
        found = self._client.bucket_exists(self._bucket)
        if not found:
            self._client.make_bucket(self._bucket)

    def bucket_exists(self) -> bool:
        return self._client.bucket_exists(self._bucket)

    # -- objects ----------------------------------------------------------

    def put_object(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """Upload an object and return its etag."""
        from io import BytesIO
        result = self._client.put_object(
            self._bucket,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
            metadata=metadata,
        )
        return result.etag

    def put_file(
        self,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """Upload a file from disk and return its etag."""
        result = self._client.fput_object(
            self._bucket,
            object_name,
            file_path,
            content_type=content_type,
            metadata=metadata,
        )
        return result.etag

    def get_object(self, object_name: str) -> bytes:
        """Download an object into memory."""
        response = self._client.get_object(self._bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_file(self, object_name: str, file_path: str) -> None:
        """Download an object to disk."""
        self._client.fget_object(self._bucket, object_name, file_path)

    def delete_object(self, object_name: str) -> None:
        self._client.remove_object(self._bucket, object_name)

    def list_objects(
        self,
        prefix: str = "",
        recursive: bool = True,
    ) -> list[str]:
        objects = self._client.list_objects(self._bucket, prefix=prefix, recursive=recursive)
        return [obj.object_name for obj in objects]

    def object_exists(self, object_name: str) -> bool:
        try:
            self._client.stat_object(self._bucket, object_name)
            return True
        except Exception:
            return False

    def presigned_get_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        return self._client.presigned_get_object(self._bucket, object_name, expires_seconds=expires_seconds)
