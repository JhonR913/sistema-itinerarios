from pydantic import BaseModel, Field


class IssueTokenRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)


class IssueTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = 60
