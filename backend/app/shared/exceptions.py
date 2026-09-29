"""Lỗi domain dùng chung toàn backend.

Services raise các lỗi dưới đây, 1 handler trung tâm trong main.py
chuyển thành response {code, detail}. Routers không raise HTTPException trực tiếp.
"""


class AppException(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    detail = "Lỗi hệ thống, vui lòng thử lại sau."

    def __init__(self, detail: str = "", code: str = "") -> None:
        self.detail = detail or self.detail
        self.code = code or self.code
        super().__init__(self.detail)


class BadRequestError(AppException):
    status_code = 400
    code = "BAD_REQUEST"
    detail = "Yêu cầu không hợp lệ."


class NotAuthorizedError(AppException):
    status_code = 403
    code = "FORBIDDEN"
    detail = "Bạn không có quyền thực hiện thao tác này."


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"
    detail = "Không tìm thấy dữ liệu."


class RoomNotFoundError(NotFoundError):
    code = "ROOM_NOT_FOUND"
    detail = "Không tìm thấy phòng."


class SessionNotFoundError(NotFoundError):
    code = "SESSION_NOT_FOUND"
    detail = "Không tìm thấy phiên học."


class MessageNotFoundError(NotFoundError):
    code = "MESSAGE_NOT_FOUND"
    detail = "Không tìm thấy tin nhắn."


class DocumentNotFoundError(NotFoundError):
    code = "DOCUMENT_NOT_FOUND"
    detail = "Không tìm thấy tài liệu."


class UserNotFoundError(NotFoundError):
    code = "USER_NOT_FOUND"
    detail = "Không tìm thấy người dùng."


class NotificationNotFoundError(NotFoundError):
    code = "NOTIFICATION_NOT_FOUND"
    detail = "Không tìm thấy thông báo."


class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT"
    detail = "Dữ liệu bị xung đột."


class RoomNameExistsError(ConflictError):
    code = "ROOM_NAME_EXISTS"
    detail = "Tên phòng đã tồn tại."


class ExternalServiceError(AppException):
    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"
    detail = "Dịch vụ ngoài không phản hồi, vui lòng thử lại sau."


class AIServiceUnavailableError(AppException):
    status_code = 503
    code = "AI_UNAVAILABLE"
    detail = "AI đang bận, vui lòng thử lại sau."
