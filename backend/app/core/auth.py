from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt
from app.core.config import settings

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24 * 30  # 30 dage


def create_token(subject: str = "owner") -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def require_auth(access_token: Optional[str] = Cookie(default=None)) -> str:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    subject = verify_token(access_token)
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return subject
