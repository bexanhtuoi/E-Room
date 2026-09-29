from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.database import get_session
from app.security import set_auth_cookie
from app.services.google_auth import google_auth_service

router = APIRouter()


@router.get("/google/login")
def google_login() -> RedirectResponse:
    return RedirectResponse(google_auth_service.get_google_login_redirect())


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_session)):
    token, expires = await google_auth_service.handle_google_callback(db, code)

    if token is None:
        return RedirectResponse(google_auth_service.frontend_redirect_url(ok=False))

    response = RedirectResponse(google_auth_service.frontend_redirect_url(ok=True))
    set_auth_cookie(response, token, expires)

    return response
