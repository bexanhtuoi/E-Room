from __future__ import annotations

import json
import os
from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from app.infrastructure.minio import MinioCRUD, _PREFIX_TTL


class TestMinioCRUDInit:
    def test_init_empty_bucket_defaults_to_settings(self) -> None:
        from app.config import settings
        mock_client = MagicMock()
        crud = MinioCRUD(client=mock_client, bucket="")
        assert crud._bucket == settings.minio_bucket
        assert crud._client is mock_client

    def test_init_with_bucket_stores_bucket_name(self) -> None:
        mock_client = MagicMock()
        crud = MinioCRUD(client=mock_client, bucket="ERoom")
        assert crud._bucket == "ERoom"
        assert crud._client is mock_client

    def test_init_with_default_client(self) -> None:
        crud = MinioCRUD(bucket="test-bucket")
        assert crud._bucket == "test-bucket"
        assert crud._client is not None


class TestBucketOperations:
    def test_ensure_bucket_creates_when_missing(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        crud = MinioCRUD(client=mock_client, bucket="ERoom")
        crud.ensure_bucket()
        mock_client.make_bucket.assert_called_once_with("ERoom")

    def test_ensure_bucket_skips_when_exists(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        crud = MinioCRUD(client=mock_client, bucket="ERoom")
        crud.ensure_bucket()
        mock_client.make_bucket.assert_not_called()

    def test_ensure_bucket_applies_lifecycle(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        crud = MinioCRUD(client=mock_client, bucket="ERoom")
        crud.ensure_bucket()
        assert mock_client.set_bucket_lifecycle.called

    def test_ensure_bucket_applies_prefix_ttl_rules(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        crud = MinioCRUD(client=mock_client, bucket="ERoom")
        crud.ensure_bucket()
        c = mock_client.set_bucket_lifecycle.call_args
        assert c is not None
        args, _ = c
        assert args[0] == "ERoom"
        config = args[1]
        rules = config.rules
        rule_ids = [r.rule_id for r in rules]
        assert "expire-audio/user_voice-1d" in rule_ids
        assert "expire-audio/ai_voice-30d" in rule_ids
        assert "expire-evidence-30d" in rule_ids

    def test_bucket_exists_delegates_to_client(self) -> None:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        assert crud.bucket_exists() is True
        mock_client.bucket_exists.assert_called_once_with("test-bucket")

    def test_prefix_ttl_config_has_expected_entries(self) -> None:
        assert "audio/user_voice/" in _PREFIX_TTL
        assert "audio/ai_voice/" in _PREFIX_TTL
        assert "evidence/" in _PREFIX_TTL
        assert _PREFIX_TTL["audio/user_voice/"] == 1
        assert _PREFIX_TTL["audio/ai_voice/"] == 30
        assert _PREFIX_TTL["evidence/"] == 30


class TestPresignedUrls:
    def test_presigned_get_url_calls_client_with_timedelta(self) -> None:
        mock_client = MagicMock()
        mock_client.presigned_get_object.return_value = "https://minio.example.com/bucket/obj?token=abc"
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        url = crud.presigned_get_url("my-object.txt", expires_seconds=1800)
        assert url == "https://minio.example.com/bucket/obj?token=abc"
        mock_client.presigned_get_object.assert_called_once_with(
            "test-bucket", "my-object.txt", expires=timedelta(seconds=1800)
        )

    def test_presigned_put_url_calls_client_with_timedelta(self) -> None:
        mock_client = MagicMock()
        mock_client.presigned_put_object.return_value = "https://minio.example.com/bucket/obj?token=xyz"
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        url = crud.presigned_put_url("upload.dat", expires_seconds=900)
        assert url == "https://minio.example.com/bucket/obj?token=xyz"
        mock_client.presigned_put_object.assert_called_once_with(
            "test-bucket", "upload.dat", expires=timedelta(seconds=900)
        )

    def test_presigned_get_url_default_expiry(self) -> None:
        mock_client = MagicMock()
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        crud.presigned_get_url("obj.bin")
        mock_client.presigned_get_object.assert_called_once_with(
            "test-bucket", "obj.bin", expires=timedelta(seconds=3600)
        )


class TestObjectOperations:
    def test_put_object_returns_etag(self) -> None:
        mock_result = MagicMock()
        mock_result.etag = "abc123def"
        mock_client = MagicMock()
        mock_client.put_object.return_value = mock_result
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        etag = crud.put_object("file.bin", b"data", content_type="application/octet-stream")
        assert etag == "abc123def"

    def test_get_object_reads_bytes(self) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"stored data"
        mock_client = MagicMock()
        mock_client.get_object.return_value = mock_response
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        result = crud.get_object("file.bin")
        assert result == b"stored data"
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_delete_object_removes_from_client(self) -> None:
        mock_client = MagicMock()
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        crud.delete_object("old-file.bin")
        mock_client.remove_object.assert_called_once_with("test-bucket", "old-file.bin")

    def test_object_exists_returns_true_on_successful_stat(self) -> None:
        mock_client = MagicMock()
        mock_client.stat_object.return_value = MagicMock()
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        assert crud.object_exists("existing.bin") is True

    def test_object_exists_returns_false_on_exception(self) -> None:
        mock_client = MagicMock()
        mock_client.stat_object.side_effect = Exception("not found")
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        assert crud.object_exists("missing.bin") is False

    def test_list_objects_returns_names(self) -> None:
        mock_obj1 = MagicMock()
        mock_obj1.object_name = "a.txt"
        mock_obj2 = MagicMock()
        mock_obj2.object_name = "b.txt"
        mock_client = MagicMock()
        mock_client.list_objects.return_value = [mock_obj1, mock_obj2]
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        result = crud.list_objects()
        assert result == ["a.txt", "b.txt"]

    def test_stat_object_returns_dict(self) -> None:
        mock_result = MagicMock()
        mock_result.size = 1024
        mock_result.etag = "etag123"
        mock_result.content_type = "text/plain"
        mock_result.last_modified = "2024-01-01"
        mock_result.metadata = {"key": "val"}
        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_result
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        stat = crud.stat_object("doc.txt")
        assert stat["size"] == 1024
        assert stat["etag"] == "etag123"
        assert stat["content_type"] == "text/plain"

    def test_put_file_returns_etag(self) -> None:
        mock_result = MagicMock()
        mock_result.etag = "file-etag-456"
        mock_client = MagicMock()
        mock_client.fput_object.return_value = mock_result
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        etag = crud.put_file("upload.txt", "/tmp/local.txt", content_type="text/plain")
        assert etag == "file-etag-456"
        mock_client.fput_object.assert_called_once_with(
            "test-bucket", "upload.txt", "/tmp/local.txt",
            content_type="text/plain", metadata=None,
        )

    def test_get_file_delegates_to_client(self) -> None:
        mock_client = MagicMock()
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        crud.get_file("remote.bin", "/tmp/out.bin")
        mock_client.fget_object.assert_called_once_with("test-bucket", "remote.bin", "/tmp/out.bin")

    def test_delete_objects_handles_errors(self) -> None:
        mock_client = MagicMock()
        mock_error = MagicMock()
        mock_client.remove_objects.return_value = [mock_error]
        crud = MinioCRUD(client=mock_client, bucket="test-bucket")
        with pytest.raises(RuntimeError, match="Failed to delete"):
            crud.delete_objects(["obj1", "obj2"])
