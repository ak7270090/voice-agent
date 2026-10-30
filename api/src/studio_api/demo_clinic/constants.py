"""City Hospital's doctors, matching clinic-voice-agent's knowledge base."""

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class Shift:
    start: time
    end: time


@dataclass(frozen=True)
class Doctor:
    id: str
    name: str
    speciality: str
    weekdays: tuple[int, ...]  # Monday is 0
    shifts: tuple[Shift, ...]
    fee: int
    # Words a caller may use instead of the doctor's name.
    keywords: tuple[str, ...]


MORNING = Shift(time(10, 0), time(13, 0))
EVENING = Shift(time(17, 0), time(20, 0))

DOCTORS = (
    Doctor(
        "dr-sharma",
        "Dr. Anil Sharma",
        "general physician",
        (0, 1, 2, 3, 4, 5),
        (MORNING, EVENING),
        500,
        ("sharma", "general", "physician", "fever", "cold", "cough"),
    ),
    Doctor(
        "dr-mehta",
        "Dr. Priya Mehta",
        "dermatologist",
        (0, 2, 4, 5),
        (Shift(time(11, 0), time(14, 0)),),
        700,
        ("mehta", "skin", "derma", "dermatologist", "rash", "acne", "hair"),
    ),
    Doctor(
        "dr-iyer",
        "Dr. Ravi Iyer",
        "paediatrician",
        (1, 3, 5),
        (MORNING, Shift(time(16, 0), time(18, 0))),
        600,
        ("iyer", "child", "kid", "baby", "paediatric", "pediatric", "paediatrician"),
    ),
    Doctor(
        "dr-khan",
        "Dr. Sana Khan",
        "orthopaedic surgeon",
        (0, 1, 2, 3, 4),
        (Shift(time(16, 0), time(19, 0)),),
        800,
        ("khan", "bone", "joint", "ortho", "knee", "back", "fracture"),
    ),
)

SLOT_MINUTES = 30
FIRST_BOOKING_NUMBER = 1001
BOOKING_ID_PREFIX = "A-"
# How many open days to suggest when the asked day has no free time.
SUGGESTED_DAYS = 3
SEARCH_DAYS_AHEAD = 14
