"""API de identidad. Las respuestas de registro, reenvio y olvido de contraseña
son identicas exista o no la cuenta (sin enumeracion de usuarios)."""
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Response

from app.domain.models import SessionTokens
from app.infrastructure.api.dependencies import Container, get_container
from app.infrastructure.api.schemas import (
    EmailRequest, LoginRequest, MessageResponse, RegisterRequest, ResetRequest, SessionResponse, VerifyRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "itinerarios_session"
_GENERIC = "Si el correo corresponde a una cuenta, te enviamos un código. Puede tardar un minuto."


def _set_cookie(response: Response, tokens: SessionTokens, c: Container) -> None:
    # httpOnly: el JavaScript de la pagina no puede leerla (un XSS no se lleva la sesion).
    # SameSite=Strict + path acotado: solo viaja a /api/auth desde este mismo sitio.
    response.set_cookie(SESSION_COOKIE, tokens.session_token, max_age=c.session_days * 86400, httponly=True,
                        secure=c.cookie_secure, samesite="strict", path="/api/auth")


def _body(tokens: SessionTokens) -> SessionResponse:
    return SessionResponse(access_token=tokens.access_token, expires_in_minutes=tokens.expires_in_minutes,
                           name=tokens.name, email=tokens.email)


@router.post("/register", status_code=202, response_model=MessageResponse)
def register(body: RegisterRequest, c: Container = Depends(get_container)):
    c.register.execute(body.email, body.name, body.password)
    return MessageResponse(message="Te enviamos un código de 6 digitos para verificar tu correo.")


@router.post("/verify", response_model=SessionResponse)
def verify(body: VerifyRequest, response: Response, c: Container = Depends(get_container)):
    tokens = c.verify.execute(body.email, body.code)
    _set_cookie(response, tokens, c)
    return _body(tokens)


@router.post("/resend", status_code=202, response_model=MessageResponse)
def resend(body: EmailRequest, c: Container = Depends(get_container)):
    c.resend.execute(body.email)
    return MessageResponse(message=_GENERIC)


@router.post("/login", response_model=SessionResponse)
def login(body: LoginRequest, response: Response, c: Container = Depends(get_container)):
    tokens = c.login.execute(body.email, body.password)
    _set_cookie(response, tokens, c)
    return _body(tokens)


@router.post("/refresh", response_model=SessionResponse)
def refresh(session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
            c: Container = Depends(get_container)):
    return _body(c.refresh.execute(session))


@router.post("/logout", status_code=204)
def logout(response: Response, session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
           c: Container = Depends(get_container)):
    c.logout.execute(session)
    response.delete_cookie(SESSION_COOKIE, path="/api/auth")
    response.status_code = 204


@router.post("/forgot", status_code=202, response_model=MessageResponse)
def forgot(body: EmailRequest, c: Container = Depends(get_container)):
    c.forgot.execute(body.email)
    return MessageResponse(message=_GENERIC)


@router.post("/reset", status_code=204)
def reset(body: ResetRequest, c: Container = Depends(get_container)):
    c.reset.execute(body.email, body.code, body.password)
