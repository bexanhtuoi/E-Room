from __future__ import annotations

import re
from typing import Optional
from uuid import UUID


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email)) and len(email) <= 254


def is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def sanitize_string(value: str, max_length: int = 1000) -> str:
    value = value.strip()
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    if len(value) > max_length:
        value = value[:max_length]
    return value


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    if len(password) < 8:
        return False, "Mật khẩu phải có ít nhất 8 ký tự"
    if not re.search(r"[A-Z]", password):
        return False, "Mật khẩu phải có ít nhất 1 chữ hoa"
    if not re.search(r"[0-9]", password):
        return False, "Mật khẩu phải có ít nhất 1 số"
    return True, None


def validate_display_name(name: str) -> tuple[bool, Optional[str]]:
    if not name or not name.strip():
        return False, "Tên hiển thị không được để trống"
    name = name.strip()
    if len(name) < 2:
        return False, "Tên hiển thị phải có ít nhất 2 ký tự"
    if len(name) > 50:
        return False, "Tên hiển thị không được quá 50 ký tự"
    if re.search(r"[<>{}]", name):
        return False, "Tên hiển thị chứa ký tự không hợp lệ"
    return True, None


def clamp(value: float, min_value: float = 0.0, max_value: float = 10.0) -> float:
    return max(min_value, min(value, max_value))
