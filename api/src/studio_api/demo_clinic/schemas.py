from datetime import date

from pydantic import BaseModel, Field


class DoctorRead(BaseModel):
    id: str
    name: str
    speciality: str
    days: list[str]
    fee: int


class Availability(BaseModel):
    doctor: str
    speciality: str
    day: date
    weekday: str
    free_times: list[str]
    # Filled when the asked day has nothing free.
    next_open_days: list[str]


class BookingRequest(BaseModel):
    patient_name: str = Field(min_length=1, max_length=120)
    patient_age: int = Field(ge=0, le=120)
    doctor: str = Field(min_length=1)
    day: date
    time: str = Field(pattern=r"^\d{2}:\d{2}$")


class BookingRead(BaseModel):
    booking_id: str
    patient_name: str
    patient_age: int
    doctor: str
    day: date
    weekday: str
    time: str
