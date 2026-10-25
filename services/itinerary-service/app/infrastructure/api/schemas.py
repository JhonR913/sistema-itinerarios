from datetime import date
from pydantic import BaseModel, Field, field_validator


class CreateItineraryRequest(BaseModel):
    nombre_usuario: str = Field(..., min_length=1, max_length=120)
    origin_airport_id: str = Field(..., min_length=1)
    destination_airport_id: str = Field(..., min_length=1)
    travel_date: date
    duration_minutes: int = Field(..., gt=0, le=2880)

    @field_validator("nombre_usuario")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("nombre_usuario no puede estar vacio")
        return v.strip()


class UpdateItineraryRequest(BaseModel):
    travel_date: date | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=2880)
    origin_airport_id: str | None = None
    destination_airport_id: str | None = None
