from functools import lru_cache
from io import BytesIO
from uuid import uuid4
from minio import Minio

from app.config import settings


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    client = get_minio_client()

    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def put_object(
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    ensure_bucket()

    result = get_minio_client().put_object(
        settings.minio_bucket,
        object_name,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )

    return result.etag


def get_object(object_name: str) -> bytes:
    response = get_minio_client().get_object(settings.minio_bucket, object_name)

    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_object(object_name: str) -> None:
    get_minio_client().remove_object(settings.minio_bucket, object_name)


def get_url(object_name: str) -> str:
    scheme = "https" if settings.minio_secure else "http"
    return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{object_name}"


def put_avatar(file_bytes: bytes, user_id: int | str) -> str:
    object_name = f"avatars/{user_id}"
    put_object(object_name, file_bytes)
    return object_name


def put_document(file_bytes: bytes, filename: str) -> str:
    object_name = f"documents/{uuid4().hex}_{filename}"
    put_object(object_name, file_bytes)
    return object_name