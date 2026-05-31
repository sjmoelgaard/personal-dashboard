from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from app.core.auth import create_token, require_auth
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


class LoginRequest(BaseModel):
    password: str


@router.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    if body.password != settings.owner_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Forkert kodeord")
    token = create_token()
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return {"ok": True}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/auth/me")
async def me(subject: str = Depends(require_auth)):
    return {"user": subject}
