import asyncio
import json

from fastapi.responses import JSONResponse

from app.main import handle_app_exception
from app.shared import DUPLICATE_TRANSCRIPT_SECONDS
from app.shared.exceptions import (
    AIServiceUnavailableError,
    AppException,
    BadRequestError,
    ConflictError,
    ExternalServiceError,
    MessageNotFoundError,
    NotAuthorizedError,
    RoomNameExistsError,
    RoomNotFoundError,
    SessionNotFoundError,
    UserNotFoundError,
)


class TestExceptionDefaults:
    def test_base_defaults(self):
        error = AppException()
        assert error.status_code == 500
        assert error.code == "INTERNAL_ERROR"
        assert error.detail

    def test_domain_errors(self):
        assert (RoomNotFoundError().status_code, RoomNotFoundError().code) == (404, "ROOM_NOT_FOUND")
        assert (SessionNotFoundError().code) == "SESSION_NOT_FOUND"
        assert (MessageNotFoundError().code) == "MESSAGE_NOT_FOUND"
        assert (UserNotFoundError().code) == "USER_NOT_FOUND"
        assert (NotAuthorizedError().status_code, NotAuthorizedError().code) == (403, "FORBIDDEN")
        assert (BadRequestError().status_code) == 400
        assert (ConflictError().status_code) == 409
        assert RoomNameExistsError().code == "ROOM_NAME_EXISTS"
        assert (ExternalServiceError().status_code) == 502
        assert (AIServiceUnavailableError().status_code) == 503

    def test_custom_detail_overrides_default(self):
        error = RoomNotFoundError(detail="Phòng 7 không tồn tại.")
        assert error.detail == "Phòng 7 không tồn tại."
        assert error.code == "ROOM_NOT_FOUND"

    def test_details_are_vietnamese(self):
        assert "Không tìm thấy phòng" in RoomNotFoundError().detail
        assert "quyền" in NotAuthorizedError().detail


class TestExceptionHandler:
    def _respond(self, error: AppException) -> JSONResponse:
        return asyncio.run(handle_app_exception(None, error))

    def test_returns_code_and_detail(self):
        response = self._respond(RoomNotFoundError())
        assert response.status_code == 404
        assert json.loads(response.body) == {
            "code": "ROOM_NOT_FOUND",
            "detail": RoomNotFoundError().detail,
        }

    def test_forbidden_shape(self):
        response = self._respond(NotAuthorizedError())
        assert response.status_code == 403
        assert json.loads(response.body)["code"] == "FORBIDDEN"


class TestSharedConstants:
    def test_duplicate_window(self):
        assert DUPLICATE_TRANSCRIPT_SECONDS == 10
