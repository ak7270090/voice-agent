"""A time comes only from the caller's own words, and a booking only from their plain yes."""

from datetime import date

import httpx
import pytest

from studio_voice.flows.runner import FlowRunner
from studio_voice.flows.schema import Flow
from studio_voice.languages import choice_readers_for, parsers_for
from studio_voice.locales.en.parser import parse_clear_yes

FRIDAY = date(2026, 10, 30)
FREE_TIMES = ["11:00", "11:30", "12:00", "12:30", "13:30"]
FLOW = {
    "nodes": [
        {"id": "start", "type": "start"},
        {
            "id": "check",
            "type": "tool",
            "data": {"name": "check_availability", "url": "http://clinic/free"},
        },
        {
            "id": "choose_time",
            "type": "step",
            "data": {
                "name": "Choose a free time",
                "fields": [{"name": "time", "type": "time", "choices_from": "free_times"}],
            },
        },
        {
            "id": "confirm",
            "type": "step",
            "data": {
                "name": "Confirm",
                "say_on_enter": "At {time}. Is that right?",
                "wait_after_enter": True,
                "on_yes": "book",
            },
        },
        {
            "id": "book",
            "type": "tool",
            "data": {
                "name": "book_appointment",
                "method": "POST",
                "url": "http://clinic/book",
                "say_while_running": "One moment while I book that.",
            },
        },
        {"id": "booked", "type": "end", "data": {"outcome": "booked", "message": "Booked."}},
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "check", "kind": "always"},
        {"id": "e2", "source": "check", "target": "choose_time", "kind": "success"},
        {"id": "e3", "source": "choose_time", "target": "confirm", "kind": "fields_complete"},
        {
            "id": "e4",
            "source": "confirm",
            "target": "book",
            "kind": "condition",
            "condition": "The caller confirms",
        },
        {
            "id": "e5",
            "source": "confirm",
            "target": "choose_time",
            "kind": "condition",
            "condition": "The caller wants a different time",
        },
        {"id": "e6", "source": "book", "target": "booked", "kind": "success"},
    ],
}


def answer_like_the_clinic(request: httpx.Request) -> httpx.Response:
    if request.method == "POST":
        return httpx.Response(201, json={"booking_id": "A-1"})
    return httpx.Response(200, json={"free_times": FREE_TIMES})


@pytest.fixture
async def runner():
    flow_runner = FlowRunner(
        Flow.model_validate(FLOW),
        httpx.AsyncClient(transport=httpx.MockTransport(answer_like_the_clinic)),
        parsers_for("en"),
        FRIDAY,
        choice_readers=choice_readers_for("en"),
    )
    await flow_runner.start()
    yield flow_runner
    await flow_runner.aclose()


async def test_a_part_of_the_day_only_narrows_what_is_offered(runner):
    await runner.take_answer("Something in the afternoon, please.")

    assert "time" not in runner.fields
    assert runner.current.id == "choose_time"
    assert "Offer only these times: 12:00, 12:30, 13:30." in runner.system_prompt("")


async def test_the_earliest_means_the_earliest_of_the_part_they_asked_for(runner):
    await runner.take_answer("Something in the afternoon, please.")
    await runner.take_answer("The earliest of those is fine.")

    assert runner.fields["time"] == "12:00"
    assert runner.current.id == "confirm"


async def test_the_earliest_with_no_part_named_is_the_earliest_free(runner):
    await runner.take_answer("The earliest you have.")

    assert runner.fields["time"] == "11:00"


async def test_a_position_in_the_list_is_not_read_as_a_clock_time(runner):
    await runner.take_answer("In the afternoon.")
    await runner.take_answer("The second one, please.")

    assert runner.fields["time"] == "12:30"


async def test_the_llm_cannot_choose_the_time(runner):
    result = await runner.save_fields({"time": "13:30"})

    assert "time" not in runner.fields
    assert runner.current.id == "choose_time"
    assert "only from the caller's own words" in result


async def test_the_llm_cannot_move_on_with_an_old_time_after_coming_back(runner):
    await runner.take_answer("Half past one.")
    await runner.enter("choose_time")
    await runner.take_answer("A different time, please.")

    await runner.save_fields({"time": "11:00"})

    assert runner.fields["time"] == "13:30"
    assert runner.current.id == "choose_time"


async def test_a_clock_time_counts_only_if_it_is_free(runner):
    await runner.take_answer("Four o'clock.")
    assert "time" not in runner.fields

    await runner.take_answer("Half past one.")
    assert runner.fields["time"] == "13:30"


async def test_a_free_time_outside_the_part_they_first_asked_for_still_counts(runner):
    await runner.take_answer("In the afternoon.")
    await runner.take_answer("Actually, eleven.")

    assert runner.fields["time"] == "11:00"


async def test_a_date_is_not_read_as_a_position_in_the_list(runner):
    await runner.take_answer("The third of November instead.")

    assert "time" not in runner.fields


async def test_a_part_with_nothing_free_tells_the_llm_to_say_so(runner):
    await runner.take_answer("In the evening.")

    assert "None of the free times" in runner.system_prompt("")


async def test_a_new_availability_result_forgets_the_part_they_asked_for(runner):
    await runner.take_answer("In the afternoon.")
    await runner.enter("check")

    await runner.take_answer("The earliest you have.")

    assert runner.fields["time"] == "11:00"


async def test_a_plain_yes_books_and_says_a_line_first(runner):
    await runner.take_answer("Half past one.")

    assert runner.line_before_answer("Yes.") == "One moment while I book that."
    await runner.take_answer("Yes.")

    assert runner.outcome == "booked"


@pytest.mark.parametrize(
    "answer",
    ["The earliest of those is fine.", "Yes, but change the time.", "Please.", "Hmm, maybe."],
)
async def test_anything_but_a_plain_yes_does_not_book(runner, answer):
    await runner.take_answer("Half past one.")

    assert runner.line_before_answer(answer) == ""
    await runner.take_answer(answer)

    assert runner.outcome is None
    assert runner.current.id == "confirm"


async def test_the_llm_has_no_way_to_start_the_booking(runner):
    await runner.take_answer("Half past one.")

    names = [tool.name for tool in runner.tools()]

    assert "go_to_book_appointment" not in names
    assert "go_to_choose_a_free_time" in names


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        ("Yes.", True),
        ("Yes, that's right.", True),
        ("Sounds good.", True),
        ("No.", None),
        ("That's not right.", None),
        ("Please.", None),
        ("Yes but on Monday instead.", None),
    ],
)
def test_clear_yes(words, expected):
    assert parse_clear_yes(words) is expected


async def test_without_the_settings_the_llm_saves_and_moves_as_before():
    plain = Flow.model_validate(
        {
            **FLOW,
            "nodes": [
                {"id": n["id"], "type": n["type"], "data": {**n.get("data", {}), "on_yes": ""}}
                if n["id"] == "confirm"
                else {
                    **n,
                    "data": {
                        **n.get("data", {}),
                        "fields": [{"name": "time", "type": "time"}],
                    },
                }
                if n["id"] == "choose_time"
                else n
                for n in FLOW["nodes"]
            ],
        }
    )
    flow_runner = FlowRunner(
        plain,
        httpx.AsyncClient(transport=httpx.MockTransport(answer_like_the_clinic)),
        parsers_for("en"),
        FRIDAY,
        choice_readers=choice_readers_for("en"),
    )
    await flow_runner.start()

    await flow_runner.save_fields({"time": "13:30"})

    assert flow_runner.fields["time"] == "13:30"
    assert "go_to_book_appointment" in [tool.name for tool in flow_runner.tools()]
    await flow_runner.aclose()
