from datetime import date, timedelta

import pytest
from studio_backend.demo_clinic.service import DoctorNotFoundError, find_doctor


def next_weekday(weekday: int) -> date:
    today = date.today()
    return today + timedelta(days=(weekday - today.weekday()) % 7 or 7)


SATURDAY = next_weekday(5)
SUNDAY = next_weekday(6)
BOOKING = {
    "patient_name": "Rohan Gupta",
    "patient_age": 34,
    "doctor": "skin",
    "day": SATURDAY.isoformat(),
    "time": "11:00",
}


@pytest.mark.parametrize(
    ("query", "doctor_id"),
    [
        ("Dr. Priya Mehta", "dr-mehta"),
        ("dermatologist", "dr-mehta"),
        ("my knee hurts", "dr-khan"),
        # First names, as a caller said on a phone call ("Priya" once matched nobody).
        ("Priya", "dr-mehta"),
        ("Dr. Anil", "dr-sharma"),
    ],
)
def test_doctor_is_found_by_name_speciality_or_problem(query, doctor_id):
    assert find_doctor(query).id == doctor_id


def test_unknown_doctor_is_not_found():
    with pytest.raises(DoctorNotFoundError):
        find_doctor("astrologer")


async def test_availability_lists_free_half_hours_in_the_doctors_shift(client):
    response = await client.get(
        "/demo-clinic/availability", params={"doctor": "Mehta", "day": SATURDAY.isoformat()}
    )

    body = response.json()
    assert body["weekday"] == "Saturday"
    assert body["free_times"] == ["11:00", "11:30", "12:00", "12:30", "13:00", "13:30"]


async def test_closed_day_suggests_the_next_open_days(client):
    response = await client.get(
        "/demo-clinic/availability", params={"doctor": "Mehta", "day": SUNDAY.isoformat()}
    )

    assert response.json()["free_times"] == []
    assert response.json()["next_open_days"][0].startswith("Monday")


async def test_booking_returns_an_id_and_takes_the_slot(client):
    first = await client.post("/demo-clinic/appointments", json=BOOKING)
    second = await client.post("/demo-clinic/appointments", json={**BOOKING, "time": "11:30"})
    taken = await client.post("/demo-clinic/appointments", json=BOOKING)
    free = (
        await client.get(
            "/demo-clinic/availability", params={"doctor": "Mehta", "day": SATURDAY.isoformat()}
        )
    ).json()["free_times"]

    assert first.json()["booking_id"] == "A-1001"
    assert first.json()["doctor"] == "Dr. Priya Mehta"
    assert second.json()["booking_id"] == "A-1002"
    assert taken.status_code == 409
    assert "11:00" not in free


async def test_a_repeated_booking_with_the_same_key_returns_the_first_booking(client):
    key = {"Idempotency-Key": "web-3f9a:book"}

    first = await client.post("/demo-clinic/appointments", json=BOOKING, headers=key)
    again = await client.post("/demo-clinic/appointments", json=BOOKING, headers=key)
    other_caller = await client.post("/demo-clinic/appointments", json=BOOKING)

    assert first.status_code == again.status_code == 201
    assert again.json()["booking_id"] == first.json()["booking_id"]
    assert other_caller.status_code == 409


async def test_unknown_doctor_cannot_be_booked_or_checked(client):
    booking = await client.post(
        "/demo-clinic/appointments", json={**BOOKING, "doctor": "astrologer"}
    )
    check = await client.get(
        "/demo-clinic/availability", params={"doctor": "astrologer", "day": SATURDAY.isoformat()}
    )

    assert booking.status_code == 404
    assert check.status_code == 404


async def test_doctors_are_listed_with_their_days(client):
    doctors = (await client.get("/demo-clinic/doctors")).json()

    assert {doctor["id"] for doctor in doctors} == {"dr-sharma", "dr-mehta", "dr-iyer", "dr-khan"}
    assert next(d for d in doctors if d["id"] == "dr-mehta")["days"] == ["Mon", "Wed", "Fri", "Sat"]
