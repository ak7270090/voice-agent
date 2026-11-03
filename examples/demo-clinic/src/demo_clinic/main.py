"""The demo clinic's HTTP API: run with `uvicorn demo_clinic.main:app`."""

from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from demo_clinic.clinic import Clinic, DoctorNotFoundError, SlotNotAvailableError
from demo_clinic.doctors import DOCTORS
from demo_clinic.schemas import Availability, BookingRead, BookingRequest, DoctorRead

WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def get_clinic(request: Request) -> Clinic:
    return request.app.state.clinic


ClinicDep = Annotated[Clinic, Depends(get_clinic)]


def create_app() -> FastAPI:
    app = FastAPI(title="Demo clinic")
    app.state.clinic = Clinic()

    @app.get("/doctors")
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

    @app.get("/availability")
    async def read_availability(doctor: str, day: date, clinic: ClinicDep) -> Availability:
        try:
            return clinic.availability(doctor, day)
        except DoctorNotFoundError as error:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"no doctor matches '{doctor}'"
            ) from error

    @app.post("/appointments", status_code=status.HTTP_201_CREATED)
    async def book_appointment(
        body: BookingRequest,
        clinic: ClinicDep,
        idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
    ) -> BookingRead:
        try:
            return clinic.book(body, idempotency_key)
        except DoctorNotFoundError as error:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"no doctor matches '{body.doctor}'"
            ) from error
        except SlotNotAvailableError as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    return app


app = create_app()
