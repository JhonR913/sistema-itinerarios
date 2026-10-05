from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
USERNAME_PATTERN = r"^[A-Za-z0-9._-]{3,50}$"
MAX_DURATION_MINUTES = 100_000  # tope de cordura


class ItineraryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(pattern=USERNAME_PATTERN)
    departure_airport_id: str = Field(pattern=ID_PATTERN)
    arrival_airport_id: str = Field(pattern=ID_PATTERN)
    travel_date: date
    duration_minutes: int = Field(gt=0, le=MAX_DURATION_MINUTES)


class ItineraryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # rechaza campos fuera de la lista blanca

    departure_airport_id: str | None = Field(default=None, pattern=ID_PATTERN)
    arrival_airport_id: str | None = Field(default=None, pattern=ID_PATTERN)
    travel_date: date | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=MAX_DURATION_MINUTES)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ItineraryUpdate":
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo a modificar")
        return self


class ItineraryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    departure_airport_id: str
    arrival_airport_id: str
    travel_date: date
    duration_minutes: int
