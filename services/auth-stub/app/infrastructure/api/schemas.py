from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=128)


class EmailRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)


class VerifyRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    code: str = Field(..., min_length=1, max_length=12)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class ResetRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    code: str = Field(..., min_length=1, max_length=12)
    password: str = Field(..., min_length=1, max_length=128)


class MessageResponse(BaseModel):
    message: str


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    name: str
    email: str
