from pydantic import BaseModel, Field


class IssueTokenRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254, description="Opcional: para recordatorios de viaje")


class IssueTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = 60
