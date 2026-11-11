from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError

from app.settings import settings

bearer_scheme = HTTPBearer()


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: Optional[str] = None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> AuthenticatedUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=["HS256"], options={"require": ["exp"]}
        )
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin subject")
    email = payload.get("email")
    return AuthenticatedUser(user_id=user_id, email=email if isinstance(email, str) and email else None)


def get_current_user_id(user: AuthenticatedUser = Depends(get_current_user)) -> str:
    return user.user_id
