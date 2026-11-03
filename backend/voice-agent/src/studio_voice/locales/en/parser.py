"""English answer parsers. Speech-to-text writes numbers both ways ("34", "thirty-four")."""

import re
from datetime import date, timedelta

UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}  # fmt: skip
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}  # fmt: skip
ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
    "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13,
    "fourteenth": 14, "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20, "thirtieth": 30,
}  # fmt: skip
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONTHS = (
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december",
)  # fmt: skip
YES_WORDS = {"yes", "yeah", "yep", "sure", "correct", "right", "okay", "ok", "confirm", "please"}
NO_WORDS = {"no", "nope", "nah", "wrong", "not", "don't", "cancel"}
# Clinic-style hours: "at 4" without am/pm means the afternoon.
AFTERNOON_HOURS_WITHOUT_SUFFIX = range(1, 8)

WORD = re.compile(r"[a-z']+|\d+")
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
CLOCK = re.compile(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?(?![\d-])")
DAY_OF_MONTH = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\b")
NOON = re.compile(r"\bnoon\b")


def words(text: str) -> list[str]:
    return WORD.findall(text.lower().replace("-", " "))


def parse_number(text: str, today: date | None = None) -> int | None:
    digits = re.search(r"\b\d+\b", text)
    if digits:
        return int(digits.group())
    total, found = 0, False
    for word in words(text):
        if word in TENS:
            total, found = total + TENS[word], True
        elif word in UNITS:
            total, found = total + UNITS[word], True
        elif found:
            break
    return total if found else None


def _ordinal_day(tokens: list[str]) -> int | None:
    for index, word in enumerate(tokens):
        if word in ORDINALS:
            value = ORDINALS[word]
            if value in (20, 30) and index + 1 < len(tokens) and tokens[index + 1] in ORDINALS:
                value += ORDINALS[tokens[index + 1]]
            return value
        if word in TENS and index + 1 < len(tokens) and tokens[index + 1] in ORDINALS:
            return TENS[word] + ORDINALS[tokens[index + 1]]
    return None


def parse_day(text: str, today: date) -> str | None:
    """'tomorrow', 'Saturday', 'next Monday', '1 November', 'the first of November', ISO."""
    lowered = text.lower()
    iso = ISO_DATE.search(lowered)
    if iso:
        return iso.group()
    tokens = words(lowered)
    if "day after tomorrow" in lowered:
        return (today + timedelta(days=2)).isoformat()
    if "tomorrow" in tokens:
        return (today + timedelta(days=1)).isoformat()
    if "today" in tokens:
        return today.isoformat()
    month = next((MONTHS.index(w) + 1 for w in tokens if w in MONTHS), None)
    if month is not None:
        numeric = DAY_OF_MONTH.search(lowered)
        day_of_month = int(numeric.group(1)) if numeric else _ordinal_day(tokens)
        if day_of_month:
            year = (
                today.year if (month, day_of_month) >= (today.month, today.day) else today.year + 1
            )
            try:
                return date(year, month, day_of_month).isoformat()
            except ValueError:
                return None
    weekday = next((WEEKDAYS.index(w) for w in tokens if w in WEEKDAYS), None)
    if weekday is not None:
        ahead = (weekday - today.weekday()) % 7 or 7
        return (today + timedelta(days=ahead)).isoformat()
    return None


def parse_time(text: str, today: date | None = None) -> str | None:
    """'11', '11:30', '4 pm', 'eleven', 'eleven thirty', 'noon'."""
    lowered = text.lower()
    # A whole word: "afternoon" contains "noon" but is not a time.
    if NOON.search(lowered):
        return "12:00"
    clock = CLOCK.search(lowered)
    if clock:
        hour, minute = int(clock.group(1)), int(clock.group(2) or 0)
        suffix = (clock.group(3) or "").replace(".", "")
    else:
        tokens = words(lowered)
        hours = [UNITS[w] for w in tokens if w in UNITS and 1 <= UNITS[w] <= 12]
        if not hours:
            return None
        hour, suffix = hours[0], ""
        minute = 30 if "thirty" in tokens or "half" in tokens else 0
        if "pm" in tokens or "evening" in tokens or "afternoon" in tokens:
            suffix = "pm"
    if suffix == "pm" and hour < 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    elif not suffix and hour in AFTERNOON_HOURS_WITHOUT_SUFFIX:
        hour += 12
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def parse_yes_no(text: str, today: date | None = None) -> bool | None:
    tokens = set(words(text))
    said_no, said_yes = bool(tokens & NO_WORDS), bool(tokens & YES_WORDS)
    if said_yes == said_no:
        return None
    return said_yes


def parse_phone(text: str, today: date | None = None) -> str | None:
    digits = re.sub(r"\D", "", text)
    return digits if 10 <= len(digits) <= 13 else None


FIELD_PARSERS = {
    "number": parse_number,
    "date": parse_day,
    "time": parse_time,
    "yes_no": parse_yes_no,
    "phone": parse_phone,
}
