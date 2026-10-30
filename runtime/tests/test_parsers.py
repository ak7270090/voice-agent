from datetime import date

import pytest

from studio_runtime.languages import UnsupportedLanguageError
from studio_runtime.parsers import parsers_for
from studio_runtime.parsers.en import (
    parse_day,
    parse_number,
    parse_phone,
    parse_time,
    parse_yes_no,
)

FRIDAY = date(2026, 10, 30)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("34", 34), ("I'm thirty-four", 34), ("age twenty one", 21), ("no idea", None)],
)
def test_numbers_are_read_as_digits_or_words(text, expected):
    assert parse_number(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("tomorrow", "2026-10-31"),
        ("day after tomorrow", "2026-11-01"),
        ("Saturday please", "2026-10-31"),
        ("next friday", "2026-11-06"),
        ("1 November", "2026-11-01"),
        ("the first of november", "2026-11-01"),
        ("on the twenty first of January", "2027-01-21"),
        ("2026-12-05", "2026-12-05"),
        ("whenever", None),
    ],
)
def test_days_are_resolved_from_today(text, expected):
    assert parse_day(text, FRIDAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("11", "11:00"),
        ("11:30", "11:30"),
        ("at 4", "16:00"),
        ("4 pm", "16:00"),
        ("10 am", "10:00"),
        ("eleven thirty", "11:30"),
        ("noon", "12:00"),
        ("not sure", None),
    ],
)
def test_times_are_read_with_clinic_style_afternoons(text, expected):
    assert parse_time(text, FRIDAY) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Yes, book it", True), ("no, wrong day", False), ("yes no", None), ("hmm", None)],
)
def test_yes_or_no_needs_one_clear_answer(text, expected):
    assert parse_yes_no(text) == expected


def test_phone_numbers_keep_only_digits():
    assert parse_phone("+91 98765 43210") == "919876543210"
    assert parse_phone("12345") is None


def test_parsers_exist_for_english_only_for_now():
    assert set(parsers_for("en")) == {"number", "date", "time", "yes_no", "phone"}
    with pytest.raises(UnsupportedLanguageError):
        parsers_for("hi")
