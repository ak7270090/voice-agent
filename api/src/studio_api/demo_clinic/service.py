from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from studio_api.demo_clinic.constants import (
    BOOKING_ID_PREFIX,
    DOCTORS,
    FIRST_BOOKING_NUMBER,
    SEARCH_DAYS_AHEAD,
    SLOT_MINUTES,
    SUGGESTED_DAYS,
    Doctor,
)
from studio_api.demo_clinic.models import DemoAppointment
from studio_api.demo_clinic.schemas import Availability, BookingRead, BookingRequest


class DoctorNotFoundError(LookupError):
    pass


class SlotNotAvailableError(ValueError):
    pass


def find_doctor(query: str) -> Doctor:
    """By id, name (or first name alone), speciality, or a word a caller might use ("skin",
    "knee")."""
    wanted = query.lower().replace("dr.", "").replace("doctor", "").strip()
    for doctor in DOCTORS:
        name_words = doctor.name.lower().replace("dr.", "").split()
        if (
            wanted in (doctor.id, doctor.name.lower(), " ".join(name_words))
            or wanted in name_words
            or wanted in doctor.speciality
        ):
            return doctor
    for doctor in DOCTORS:
        if any(keyword in wanted for keyword in doctor.keywords):
            return doctor
    raise DoctorNotFoundError(query)


def all_slots(doctor: Doctor, day: date) -> list[str]:
    if day.weekday() not in doctor.weekdays:
        return []
    slots = []
    for shift in doctor.shifts:
        moment = datetime.combine(day, shift.start)
        while moment.time() < shift.end:
            slots.append(moment.strftime("%H:%M"))
            moment += timedelta(minutes=SLOT_MINUTES)
    return slots


async def free_slots(session: AsyncSession, doctor: Doctor, day: date) -> list[str]:
    booked = set(
        await session.scalars(
            select(DemoAppointment.time).where(
                DemoAppointment.doctor_id == doctor.id, DemoAppointment.day == day
            )
        )
    )
    return [slot for slot in all_slots(doctor, day) if slot not in booked]


async def availability(session: AsyncSession, doctor_query: str, day: date) -> Availability:
    doctor = find_doctor(doctor_query)
    free = await free_slots(session, doctor, day)
    next_days = []
    candidate = day
    while (
        not free
        and len(next_days) < SUGGESTED_DAYS
        and candidate < day + timedelta(days=SEARCH_DAYS_AHEAD)
    ):
        candidate += timedelta(days=1)
        if await free_slots(session, doctor, candidate):
            next_days.append(f"{candidate:%A} {candidate.isoformat()}")
    return Availability(
        doctor=doctor.name,
        speciality=doctor.speciality,
        day=day,
        weekday=f"{day:%A}",
        free_times=free,
        next_open_days=next_days,
    )


async def book(
    session: AsyncSession, request: BookingRequest, idempotency_key: str | None = None
) -> BookingRead:
    """A repeated request with the same idempotency key (a retry, or one that was cut off)
    gets the booking it already made, not a second one or a "slot taken" error."""
    if idempotency_key and (earlier := await _booked_with(session, idempotency_key)):
        return booking_read(earlier)
    doctor = find_doctor(request.doctor)
    if request.time not in await free_slots(session, doctor, request.day):
        raise SlotNotAvailableError(f"{doctor.name} is not free on {request.day} at {request.time}")
    last = await session.scalar(select(func.max(DemoAppointment.booking_number)))
    appointment = DemoAppointment(
        booking_number=(last or FIRST_BOOKING_NUMBER - 1) + 1,
        patient_name=request.patient_name,
        patient_age=request.patient_age,
        doctor_id=doctor.id,
        day=request.day,
        time=request.time,
        idempotency_key=idempotency_key,
    )
    session.add(appointment)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if idempotency_key and (earlier := await _booked_with(session, idempotency_key)):
            return booking_read(earlier)
        raise SlotNotAvailableError("that slot was just taken") from error
    return booking_read(appointment)


async def _booked_with(session: AsyncSession, idempotency_key: str) -> DemoAppointment | None:
    return await session.scalar(
        select(DemoAppointment).where(DemoAppointment.idempotency_key == idempotency_key)
    )


def booking_read(appointment: DemoAppointment) -> BookingRead:
    return BookingRead(
        booking_id=f"{BOOKING_ID_PREFIX}{appointment.booking_number}",
        patient_name=appointment.patient_name,
        patient_age=appointment.patient_age,
        doctor=next(doctor.name for doctor in DOCTORS if doctor.id == appointment.doctor_id),
        day=appointment.day,
        weekday=f"{appointment.day:%A}",
        time=appointment.time,
    )
