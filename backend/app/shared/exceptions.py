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


class NotAuthenticatedError(AppException):
    status_code = 403
    code = "UNAUTHENTICATED"
    detail = "Chưa đăng nhập."


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


class UtteranceNotFoundError(NotFoundError):
    code = "UTTERANCE_NOT_FOUND"
    detail = "Không tìm thấy lượt nói."


class NothingToScoreError(BadRequestError):
    code = "NOTHING_TO_SCORE"
    detail = "Không có gì để chấm."


class DocumentNotFoundError(NotFoundError):
    code = "DOCUMENT_NOT_FOUND"
    detail = "Không tìm thấy tài liệu."


class UserNotFoundError(NotFoundError):
    code = "USER_NOT_FOUND"
    detail = "Không tìm thấy người dùng."


class NotificationNotFoundError(NotFoundError):
    code = "NOTIFICATION_NOT_FOUND"
    detail = "Không tìm thấy thông báo."


class AvatarNotFoundError(NotFoundError):
    code = "AVATAR_NOT_FOUND"
    detail = "Không tìm thấy ảnh đại diện."


class EmailExistsError(BadRequestError):
    code = "EMAIL_EXISTS"
    detail = "Email đã được đăng ký."


class InvalidCredentialsError(BadRequestError):
    code = "INVALID_CREDENTIALS"
    detail = "Email hoặc mật khẩu không đúng."


class GoogleNotConfiguredError(BadRequestError):
    code = "GOOGLE_NOT_CONFIGURED"
    detail = "Đăng nhập Google chưa được cấu hình (thiếu GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET)."


class TTSUnavailableError(AppException):
    status_code = 502
    code = "TTS_UNAVAILABLE"
    detail = "Máy chủ TTS không khả dụng."


class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT"
    detail = "Dữ liệu bị xung đột."


class NoScoredUtterancesError(ConflictError):
    code = "SESSION_NO_SCORED_UTTERANCES"
    detail = "Chưa có câu nào được chấm điểm trong session này. Hãy chấm điểm từng câu trước."


class RoomNameExistsError(ConflictError):
    code = "ROOM_NAME_EXISTS"
    detail = "Tên phòng đã tồn tại."


class NoScoreReportError(ConflictError):
    code = "NO_SCORE_REPORT"
    detail = "Chưa có điểm phát âm. Hãy chấm điểm trước."


class RoomFullError(AppException):
    status_code = 403
    code = "ROOM_FULL"
    detail = "Phòng đã đầy."


class NoOpenRoomsError(NotFoundError):
    code = "NO_OPEN_ROOMS"
    detail = "Hiện không có phòng nào mở. Hãy tạo phòng mới!"


class PresenceUnavailableError(AppException):
    status_code = 503
    code = "PRESENCE_UNAVAILABLE"
    detail = "Dịch vụ hiện diện không khả dụng."


class WebhookAuthError(AppException):
    status_code = 401
    code = "WEBHOOK_UNAUTHORIZED"
    detail = "Webhook không hợp lệ."


class ExternalServiceError(AppException):
    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"
    detail = "Dịch vụ ngoài không phản hồi, vui lòng thử lại sau."


class AIServiceUnavailableError(AppException):
    status_code = 503
    code = "AI_UNAVAILABLE"
    detail = "AI đang bận, vui lòng thử lại sau."


class ScoringQueueError(AppException):
    status_code = 503
    code = "SCORING_QUEUE_UNAVAILABLE"
    detail = "Hàng đợi chấm điểm không khả dụng."
