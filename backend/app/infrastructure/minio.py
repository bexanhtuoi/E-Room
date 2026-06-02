from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.commonconfig import ENABLED
from minio.deleteobjects import DeleteObject
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration

from app.config import settings


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


# Prefix-level TTL (in days). Only objects under these prefixes get auto-expired.
_PREFIX_TTL = {
    "audio/user_voice/": 1,   # user voice recordings expire after 1 day
    "audio/ai_voice/": 30,    # AI TTS cache lives 30 days
    "evidence/": 30,          # evidence files expire after 30 days
}


class MinioCRUD:
    def __init__(
        self,
        client: Optional[Minio] = None,
        bucket: str = "",
    ) -> None:
        self._client = client or get_minio_client()
        self._bucket = bucket or settings.minio_bucket

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            self._apply_lifecycle()

    def _apply_lifecycle(self) -> None:
        """Apply prefix-level TTL rules to the bucket."""
        rules: list[Rule] = []
        for prefix, days in _PREFIX_TTL.items():
            rules.append(
                Rule(
                    ENABLED,
                    rule_filter=None,
                    rule_id=f"expire-{prefix.strip('/')}-{days}d",
                    expiration=Expiration(days=days),
                )
            )
        if not rules:
            return
        config = LifecycleConfig(rules)
        self._client.set_bucket_lifecycle(self._bucket, config)

    def bucket_exists(self) -> bool:
        return self._client.bucket_exists(self._bucket)

    def put_object(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
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
        result = self._client.fput_object(
            self._bucket,
            object_name,
            file_path,
            content_type=content_type,
            metadata=metadata,
        )
        return result.etag

    def get_object(self, object_name: str) -> bytes:
        response = self._client.get_object(self._bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_file(self, object_name: str, file_path: str) -> None:
        self._client.fget_object(self._bucket, object_name, file_path)

    def delete_object(self, object_name: str) -> None:
        self._client.remove_object(self._bucket, object_name)

    def delete_objects(self, object_names: list[str]) -> None:
        errors = self._client.remove_objects(
            self._bucket,
            [DeleteObject(name) for name in object_names],
        )
        for error in errors:
            raise RuntimeError(f"Failed to delete {error}")

    def list_objects(self, prefix: str = "", recursive: bool = True) -> list[str]:
        objects = self._client.list_objects(self._bucket, prefix=prefix, recursive=recursive)
        return [obj.object_name for obj in objects]

    def stat_object(self, object_name: str) -> dict:
        result = self._client.stat_object(self._bucket, object_name)
        return {
            "size": result.size,
            "etag": result.etag,
            "content_type": result.content_type,
            "last_modified": result.last_modified,
            "metadata": result.metadata,
        }

    def object_exists(self, object_name: str) -> bool:
        try:
            self._client.stat_object(self._bucket, object_name)
            return True
        except Exception:
            return False

    def presigned_get_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        return self._client.presigned_get_object(
            self._bucket, object_name, expires=timedelta(seconds=expires_seconds)
        )

    def presigned_put_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        return self._client.presigned_put_object(
            self._bucket, object_name, expires=timedelta(seconds=expires_seconds)
        )
