"""Unico endpoint de este servicio. RF-014 en Documento_Requerimientos.docx.
Deliberadamente NO hay registro, NO hay contraseña: es un stub, no un
servicio de identidad (decision documentada, ver Documento_Arquitectura.docx
seccion 12 y Plan_de_Blindaje_Seguridad.docx)."""
from fastapi import APIRouter, Depends, HTTPException

from app.application.use_cases import IssueToken
from app.domain.ports import TokenIssuerPort
from app.infrastructure.api.dependencies import get_token_issuer
from app.infrastructure.api.schemas import IssueTokenRequest, IssueTokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token", response_model=IssueTokenResponse)
def issue_token(
    body: IssueTokenRequest,
    issuer: TokenIssuerPort = Depends(get_token_issuer),
):
    try:
        token = IssueToken(issuer).execute(body.username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return IssueTokenResponse(access_token=token)
