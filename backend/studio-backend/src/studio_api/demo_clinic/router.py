from datetime import date
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from studio_api.database import SessionDep
from studio_api.demo_clinic import service
from studio_api.demo_clinic.constants import DOCTORS
from studio_api.demo_clinic.schemas import Availability, BookingRead, BookingRequest, DoctorRead

WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

router = APIRouter(prefix="/demo-clinic", tags=["demo clinic"])


@router.get("/doctors")
async def list_doctors() -> list[DoctorRead]:
    return [
        DoctorRead(
            id=doctor.id,
            name=doctor.name,
            speciality=doctor.speciality,
            days=[WEEKDAY_NAMES[day] for day in doctor.weekdays],
            fee=doctor.fee,
        )
        for doctor in DOCTORS
    ]


@router.get("/availability")
async def read_availability(doctor: str, day: date, session: SessionDep) -> Availability:
    try:
        return await service.availability(session, doctor, day)
    except service.DoctorNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no doctor matches '{doctor}'") from error


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
async def book_appointment(
    body: BookingRequest,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
) -> BookingRead:
    try:
        return await service.book(session, body, idempotency_key)
    except service.DoctorNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no doctor matches '{body.doctor}'"
        ) from error
    except service.SlotNotAvailableError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
