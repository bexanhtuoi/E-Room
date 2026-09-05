from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.ai.tools import retrieval_documents
from app.database import engine
from app.services import document_crud
from tests.conftest import switch_to


class TestRAGPipelineE2E:
    @pytest.mark.asyncio
    async def test_document_upload_and_rag_query_e2e(self, client: TestClient, alice: dict):
        switch_to(client, alice)

        # 1. Luu document vao he thong
        doc_res = client.post(
            "/api/v1/documents/",
            json={
                "file_name": "idioms.pdf",
                "file_type": "pdf",
                "file_path": "documents/idioms.pdf",
                "metadata_json": '{"tag": "idioms"}',
            },
        )
        assert doc_res.status_code == 201
        doc_data = doc_res.json()
        assert doc_data["file_name"] == "idioms.pdf"

        # Kiem tra da luu vao DB
        with Session(engine) as db:
            db_doc = document_crud.get_one(db, id=doc_data["id"])
            assert db_doc is not None
            assert db_doc.file_name == "idioms.pdf"

        # 2. Truy van qua Tool RAG Retrieval cua AI Agent
        with patch("app.ai.tools.retrieve_relevant_documents") as mock_retrieve:
            mock_retrieve.return_value = [{"text": "Break a leg means good luck."}]

            retrieval_output = await retrieval_documents.ainvoke({"query": "What does break a leg mean?"})
            assert isinstance(retrieval_output, list)
            assert len(retrieval_output) == 1
            assert "good luck" in retrieval_output[0]["text"]
            assert mock_retrieve.called
