"""Doctors' free times and bookings, kept in memory: a restart empties the appointment book."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from demo_clinic.doctors import (
    BOOKING_ID_PREFIX,
    DOCTORS,
    FIRST_BOOKING_NUMBER,
    SEARCH_DAYS_AHEAD,
    SLOT_MINUTES,
    SUGGESTED_DAYS,
    Doctor,
)
from demo_clinic.schemas import Availability, BookingRead, BookingRequest


class DoctorNotFoundError(LookupError):
    pass


class SlotNotAvailableError(ValueError):
    pass


@dataclass(frozen=True)
class Appointment:
    booking_number: int
    patient_name: str
    patient_age: int
    doctor: Doctor
    day: date
    time: str


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


def booking_read(appointment: Appointment) -> BookingRead:
    return BookingRead(
        booking_id=f"{BOOKING_ID_PREFIX}{appointment.booking_number}",
        patient_name=appointment.patient_name,
        patient_age=appointment.patient_age,
        doctor=appointment.doctor.name,
        day=appointment.day,
        weekday=f"{appointment.day:%A}",
        time=appointment.time,
    )


class Clinic:
    """Nothing here awaits, so a check and the booking after it can't interleave with another
    request on the server's one event loop."""

    def __init__(self) -> None:
        self._by_slot: dict[tuple[str, date, str], Appointment] = {}
        self._by_idempotency_key: dict[str, Appointment] = {}

    def free_slots(self, doctor: Doctor, day: date) -> list[str]:
        return [
            slot for slot in all_slots(doctor, day) if (doctor.id, day, slot) not in self._by_slot
        ]

    def availability(self, doctor_query: str, day: date) -> Availability:
        doctor = find_doctor(doctor_query)
        free = self.free_slots(doctor, day)
        next_days = []
        candidate = day
        while (
            not free
            and len(next_days) < SUGGESTED_DAYS
            and candidate < day + timedelta(days=SEARCH_DAYS_AHEAD)
        ):
            candidate += timedelta(days=1)
            if self.free_slots(doctor, candidate):
                next_days.append(f"{candidate:%A} {candidate.isoformat()}")
        return Availability(
            doctor=doctor.name,
            speciality=doctor.speciality,
            day=day,
            weekday=f"{day:%A}",
            free_times=free,
            next_open_days=next_days,
        )

    def book(self, request: BookingRequest, idempotency_key: str | None = None) -> BookingRead:
        """A repeated request with the same idempotency key (a retry, or one that was cut off)
        gets the booking it already made, not a second one or a "slot taken" error."""
        if idempotency_key and (earlier := self._by_idempotency_key.get(idempotency_key)):
            return booking_read(earlier)
        doctor = find_doctor(request.doctor)
        if request.time not in self.free_slots(doctor, request.day):
            raise SlotNotAvailableError(
                f"{doctor.name} is not free on {request.day} at {request.time}"
            )
        appointment = Appointment(
            booking_number=FIRST_BOOKING_NUMBER + len(self._by_slot),
            patient_name=request.patient_name,
            patient_age=request.patient_age,
            doctor=doctor,
            day=request.day,
            time=request.time,
        )
        self._by_slot[(doctor.id, request.day, request.time)] = appointment
        if idempotency_key:
            self._by_idempotency_key[idempotency_key] = appointment
        return booking_read(appointment)
