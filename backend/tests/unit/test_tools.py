from unittest.mock import AsyncMock, patch

import pytest

from app.ai.tools import make_room_retrieval_tool


class TestMakeRoomRetrievalTool:
    @pytest.mark.asyncio
    async def test_forces_room_tag(self):
        scoped = make_room_retrieval_tool(90001)

        with patch("app.ai.tools.retrieve_relevant_documents", new=AsyncMock(return_value=[])) as mock_retrieve:
            await scoped.ainvoke({"query": "eroom", "k": 5})

        assert mock_retrieve.call_args[0][:3] == ("eroom", 5, "room:90001")

    def test_schema_has_no_tag_param(self):
        scoped = make_room_retrieval_tool(90001)
        assert scoped.name == "retrieval_documents"
        assert "tag" not in (scoped.args or {})

    @pytest.mark.asyncio
    async def test_different_rooms_get_different_tags(self):
        with patch("app.ai.tools.retrieve_relevant_documents", new=AsyncMock(return_value=[])) as mock_retrieve:
            await make_room_retrieval_tool(60002).ainvoke({"query": "eroom"})

        assert mock_retrieve.call_args[0][2] == "room:60002"
