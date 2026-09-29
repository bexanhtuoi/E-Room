from datetime import timedelta
from urllib.parse import urlencode

import httpx
from sqlmodel import Session

from app.config import settings
from app.repositories.user import user_crud
from app.security import create_access_token
from app.services.base import ServiceBase
from app.shared.exceptions import GoogleNotConfiguredError

__all__ = [
    "GoogleAuthService",
    "google_auth_service",
]

TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleAuthService(ServiceBase):
    def get_google_login_redirect(self, ) -> str:
        # Endpoint này chỉ mở bằng browser — chưa cấu hình thì đưa user về login.
        if not settings.google_client_id or not settings.google_client_secret:
            return self.frontend_redirect_url(ok=False)

        return self.google_auth_url()



    def google_auth_url(self, state: str = "") -> str:
        params = {
            "client_id": settings.google_client_id,
            "response_type": "code",
            "redirect_uri": settings.google_redirect_uri,
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)



    def frontend_redirect_url(self, ok: bool) -> str:
        base = settings.frontend_url.rstrip("/")
        suffix = "/rooms?google=ok" if ok else "/login?google=error"

        return f"{base}{suffix}"



    def ensure_google_configured(self, ) -> None:
        if not settings.google_client_id or not settings.google_client_secret:
            raise GoogleNotConfiguredError()



    async def fetch_google_profile(self, code: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                token_resp = await client.post(
                    TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": settings.google_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if token_resp.status_code != 200:
                    return None

                google_access_token = token_resp.json().get("access_token")

                if not google_access_token:
                    return None

                userinfo_resp = await client.get(
                    USERINFO_URL,
                    headers={"Authorization": f"Bearer {google_access_token}"},
                )

                if userinfo_resp.status_code != 200:
                    return None

                return userinfo_resp.json()
        except httpx.HTTPError:
            return None



    def find_or_create_google_user(self, db: Session, info: dict):
        email = (info.get("email") or "").strip().lower()

        if not email:
            return None

        user = user_crud.get_one(db, email=email)

        if user is None:
            # Tài khoản Google mới — tạo user không mật khẩu, avatar lấy từ Google.
            return user_crud.create(
                db,
                obj_in={
                    "email": email,
                    "full_name": info.get("name") or email.split("@")[0],
                    "avatar_url": info.get("picture"),
                    "password_hash": None,
                },
            )

        if not user.avatar_url and info.get("picture"):
            user_crud.update(db, db_obj=user, obj_in={"avatar_url": info.get("picture")})

        return user



    async def handle_google_callback(self, db: Session, code: str):
        self.ensure_google_configured()

        info = await self.fetch_google_profile(code)
        user = self.find_or_create_google_user(db, info or {})

        if user is None:
            return None, None

        expires = timedelta(minutes=settings.access_token_expires_minutes)
        token = create_access_token(data=user.id, expires_delta=expires)

        return token, expires



google_auth_service = GoogleAuthService()
