from __future__ import annotations

import pytest


class TestRoomAPI:
    def test_list_rooms_empty(self, client):
        response = client.get("/api/v1/rooms/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_room_requires_auth(self, client):
        response = client.post("/api/v1/rooms/", json={
            "topic": "Test Room",
            "tag_ids": [],
            "max_participants": 5,
            "is_public": True,
        })
        assert response.status_code in (401, 403)

    def test_create_room(self, client, auth_headers):
        response = client.post("/api/v1/rooms/", json={
            "topic": "English Practice",
            "tag_ids": [],
            "max_participants": 4,
            "is_public": True,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "English Practice"
        assert data["status"] in ("MATCHING", "IDLE")
        assert data["max_participants"] == 4

    def test_get_room_by_id(self, client, auth_headers):
        create_resp = client.post("/api/v1/rooms/", json={
            "topic": "Get Room Test",
            "tag_ids": [],
            "max_participants": 5,
            "is_public": True,
        }, headers=auth_headers)
        room_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/rooms/{room_id}")
        assert response.status_code == 200
        assert response.json()["id"] == room_id

    def test_get_nonexistent_room(self, client):
        response = client.get("/api/v1/rooms/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_join_room(self, client, auth_headers):
        create_resp = client.post("/api/v1/rooms/", json={
            "topic": "Join Room",
            "tag_ids": [],
            "max_participants": 5,
            "is_public": True,
        }, headers=auth_headers)
        room_id = create_resp.json()["id"]

        join_resp = client.post(f"/api/v1/rooms/{room_id}/join", json={
            "user_id": "00000000-0000-0000-0000-000000000001",
        })
        assert join_resp.status_code == 200
        assert join_resp.json()["status"] == "joined"

    def test_join_nonexistent_room(self, client):
        response = client.post("/api/v1/rooms/00000000-0000-0000-0000-000000000000/join", json={
            "user_id": "00000000-0000-0000-0000-000000000001",
        })
        assert response.status_code == 404

    def test_leave_room(self, client, auth_headers):
        create_resp = client.post("/api/v1/rooms/", json={
            "topic": "Leave Room",
            "tag_ids": [],
            "max_participants": 5,
            "is_public": True,
        }, headers=auth_headers)
        room_id = create_resp.json()["id"]

        join_resp = client.post(f"/api/v1/rooms/{room_id}/join", json={
            "user_id": "00000000-0000-0000-0000-000000000001",
        })
        assert join_resp.status_code == 200

        leave_resp = client.post(f"/api/v1/rooms/{room_id}/leave", json={
            "user_id": "00000000-0000-0000-0000-000000000001",
        })
        assert leave_resp.status_code == 200
        assert leave_resp.json()["status"] == "left"

    def test_room_full(self, client, auth_headers):
        create_resp = client.post("/api/v1/rooms/", json={
            "topic": "Full Room",
            "tag_ids": [],
            "max_participants": 3,
            "is_public": True,
        }, headers=auth_headers)
        room_id = create_resp.json()["id"]

        for i in range(3):
            client.post(f"/api/v1/rooms/{room_id}/join", json={
                "user_id": f"00000000-0000-0000-0000-00000000000{i}",
            })

        response = client.post(f"/api/v1/rooms/{room_id}/join", json={
            "user_id": "00000000-0000-0000-0000-000000000009",
        })
        assert response.status_code == 400

    def test_match_room(self, client, auth_headers):
        create_resp = client.post("/api/v1/rooms/", json={
            "topic": "Match Room",
            "tag_ids": ["vocabulary"],
            "max_participants": 5,
            "is_public": True,
        }, headers=auth_headers)

        response = client.post("/api/v1/rooms/match", json={
            "user_id": "00000000-0000-0000-0000-000000000001",
            "tag_ids": ["vocabulary"],
        })
        assert response.status_code == 200
        assert response.json()["status"] in ("matched", "queued")

    def test_get_room_token_requires_auth(self, client):
        response = client.post("/api/v1/rooms/00000000-0000-0000-0000-000000000001/token")
        assert response.status_code in (401, 403)

    def test_invalid_room_id(self, client):
        response = client.get("/api/v1/rooms/not-a-uuid")
        assert response.status_code == 422


class TestPagination:
    def test_list_with_pagination(self, client):
        response = client.get("/api/v1/rooms/?skip=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_negative_skip(self, client):
        response = client.get("/api/v1/rooms/?skip=-1&limit=5")
        assert response.status_code == 422

    def test_limit_exceeds_max(self, client):
        response = client.get("/api/v1/rooms/?skip=0&limit=200")
        assert response.status_code == 422

    def test_zero_limit(self, client):
        response = client.get("/api/v1/rooms/?skip=0&limit=0")
        assert response.status_code == 422
