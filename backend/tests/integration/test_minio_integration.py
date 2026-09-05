from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.integration.minio import get_object, put_document, put_object


class TestMinioIntegration:
    def test_put_and_get_object_mock(self):
        mock_minio_client = MagicMock()
        mock_minio_client.bucket_exists.return_value = True
        mock_response = MagicMock()
        mock_response.read.return_value = b"Fake File Content"
        mock_minio_client.get_object.return_value = mock_response

        with patch("app.integration.minio.get_minio_client", return_value=mock_minio_client):
            put_object("test/file.txt", b"Fake File Content")
            assert mock_minio_client.put_object.called

            content = get_object("test/file.txt")
            assert content == b"Fake File Content"

    def test_put_document_file(self):
        mock_minio_client = MagicMock()
        mock_minio_client.bucket_exists.return_value = True

        with patch("app.integration.minio.get_minio_client", return_value=mock_minio_client):
            obj_name = put_document(b"%PDF-1.4...", "lesson1.pdf")
            assert obj_name.startswith("documents/")
            assert obj_name.endswith("_lesson1.pdf")
            assert mock_minio_client.put_object.called
