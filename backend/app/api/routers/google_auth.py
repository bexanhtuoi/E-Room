from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.models import User
from app.security import create_access_token, hash_password
from app.services import user_crud

router = APIRouter()

TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def google_auth_url(state: str = "") -> str:
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


def frontend_redirect(ok: bool) -> RedirectResponse:
    base = settings.frontend_url.rstrip("/")
    suffix = "/rooms?google=ok" if ok else "/login?google=error"
    return RedirectResponse(f"{base}{suffix}", status_code=302)


def set_auth_cookie(response: JSONResponse | RedirectResponse, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
    )


@router.get("/google/login")
def google_login() -> RedirectResponse:
    if not settings.google_client_id or not settings.google_client_secret:
        # Endpoint nay chi mo bang browser — dua user ve login thay vi tra JSON tho.
        return frontend_redirect(ok=False)
    return RedirectResponse(google_auth_url())


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_session)):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google login is not configured (missing GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET)",
        )

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
                return frontend_redirect(ok=False)

            google_access_token = token_resp.json().get("access_token")
            if not google_access_token:
                return frontend_redirect(ok=False)

            userinfo_resp = await client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
            )
            if userinfo_resp.status_code != 200:
                return frontend_redirect(ok=False)

            info = userinfo_resp.json()
    except httpx.HTTPError:
        return frontend_redirect(ok=False)

    email = (info.get("email") or "").strip().lower()
    if not email:
        return frontend_redirect(ok=False)

    db_user = user_crud.get_one(db, email=email)
    if db_user is None:
        # Tai khoan Google moi — tao user khong mat khau, avatar lay tu Google
        db_user = user_crud.create(
            db,
            obj_in={
                "email": email,
                "full_name": info.get("name") or email.split("@")[0],
                "avatar_url": info.get("picture"),
                "password_hash": None,
            },
        )
    elif not db_user.avatar_url and info.get("picture"):
        user_crud.update(db, db_obj=db_user, obj_in={"avatar_url": info.get("picture")})

    jwt_token = create_access_token(
        data=db_user.id,
        expires_delta=timedelta(minutes=settings.access_token_expires_minutes),
    )

    response = frontend_redirect(ok=True)
    set_auth_cookie(response, jwt_token)
    return response
