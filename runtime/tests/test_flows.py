"""Running a clinic-style flow with a scripted LLM and a fake clinic API: no model is called."""

import asyncio
import json
from datetime import date

import httpx
import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from studio_runtime.flows.graph import FlowGraph
from studio_runtime.flows.runner import FlowRunner, value_at
from studio_runtime.flows.schema import Flow
from studio_runtime.parsers import parsers_for

FRIDAY = date(2026, 10, 30)
CLINIC = "http://clinic"
FLOW = {
    "nodes": [
        {"id": "start", "type": "start"},
        {
            "id": "greet",
            "type": "step",
            "data": {"name": "Greet", "instructions": "Ask how to help."},
        },
        {
            "id": "collect",
            "type": "step",
            "data": {
                "name": "Collect booking details",
                "fields": [
                    {"name": "patient_name", "type": "name"},
                    {"name": "patient_age", "type": "number"},
                    {"name": "day", "type": "date"},
                    {"name": "time", "type": "time"},
                ],
                "tools": ["check"],
                "say_on_enter": "Sure.",
            },
        },
        {"id": "confirm", "type": "step", "data": {"name": "Confirm"}},
        {
            "id": "check",
            "type": "tool",
            "data": {
                "name": "check_availability",
                "url": CLINIC + "/availability?day={day}",
                "say_while_running": "One moment.",
                "save_to_fields": {"day": "day"},
            },
        },
        {
            "id": "book",
            "type": "tool",
            "data": {
                "name": "book_appointment",
                "method": "POST",
                "url": CLINIC + "/appointments",
                "body": {
                    "patient_name": "{patient_name}",
                    "patient_age": "{patient_age}",
                    "when": "{day} {time}",
                },
            },
        },
        {
            "id": "booked",
            "type": "end",
            "data": {"outcome": "booked", "message": "Booked: {booking_id}."},
        },
        {
            "id": "help",
            "type": "global",
            "data": {"name": "Human", "condition": "Caller wants a person"},
        },
        {"id": "desk", "type": "transfer", "data": {"message": "Connecting you."}},
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "greet", "kind": "always"},
        {"id": "e2", "source": "greet", "target": "collect", "condition": "Caller wants to book"},
        {"id": "e3", "source": "collect", "target": "confirm", "kind": "fields_complete"},
        {"id": "e4", "source": "confirm", "target": "book", "condition": "Caller confirms"},
        {
            "id": "e5",
            "source": "confirm",
            "target": "collect",
            "condition": "Caller changes a detail",
        },
        {"id": "e6", "source": "book", "target": "booked", "kind": "success"},
        {"id": "e7", "source": "book", "target": "collect", "kind": "failure"},
        {"id": "e8", "source": "help", "target": "desk", "kind": "always"},
    ],
}


class FakeClinic:
    def __init__(self, booking_status: int = 201, delay_seconds: float = 0) -> None:
        self.requests: list[httpx.Request] = []
        self.booking_status = booking_status
        self.delay_seconds = delay_seconds

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        await asyncio.sleep(self.delay_seconds)
        if request.url.path == "/availability":
            day = request.url.params["day"]
            return httpx.Response(200, json={"free_times": ["11:00", "11:30"], "day": day})
        return httpx.Response(self.booking_status, json={"booking_id": "A-1001"})


def make_runner(clinic: FakeClinic | None = None) -> FlowRunner:
    http = httpx.AsyncClient(transport=httpx.MockTransport(clinic or FakeClinic()))
    return FlowRunner(Flow.model_validate(FLOW), http, parsers_for("en"), FRIDAY)


class ScriptedModel(BaseChatModel):
    """Replies with the scripted messages in order and remembers what it was shown."""

    script: list[AIMessage]
    seen: list[list] = []
    bound: list[list[str]] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        self.bound.append([tool.name for tool in tools])
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.seen.append(messages)
        return ChatResult(generations=[ChatGeneration(message=self.script.pop(0))])


def call(name: str, **args) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{name}"}])


async def run_turn(graph: FlowGraph, user_text: str) -> str:
    state = {"messages": [SystemMessage("base"), HumanMessage(user_text)]}
    return "".join([chunk.text async for chunk, _ in graph.astream(state)])


async def test_flow_starts_at_the_first_step():
    runner = make_runner()

    await runner.start()

    assert runner.current.id == "greet"
    assert runner.path == ["start", "greet"]


async def test_typed_answers_are_read_from_the_callers_words_before_the_llm():
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")
    runner.fields["patient_name"] = "Rohan Gupta"

    await runner.take_answer("I'm thirty-four")
    await runner.take_answer("Saturday")

    assert runner.fields["patient_age"] == 34
    assert runner.fields["day"] == "2026-10-31"
    assert "day (date): have 2026-10-31 (Saturday)" in runner.system_prompt("base")


async def test_filling_every_field_books_after_confirmation_and_ends_with_the_booking_id():
    clinic = FakeClinic()
    runner = make_runner(clinic)
    await runner.start()
    await runner.enter("collect")

    status = await runner.save_fields(
        {"patient_name": "Rohan Gupta", "patient_age": "34", "day": "Saturday", "time": "11"}
    )
    confirm_move = next(t for t in runner.tools() if t.description == "Caller confirms")
    assert confirm_move.name == "go_to_book_appointment"
    await confirm_move.ainvoke({})

    body = json.loads(clinic.requests[0].content)
    assert "Moved on to: Confirm." in status
    assert body == {"patient_name": "Rohan Gupta", "patient_age": 34, "when": "2026-10-31 11:00"}
    assert runner.ended and runner.outcome == "booked"
    assert runner.final_message == "Booked: A-1001."
    assert runner.path == ["start", "greet", "collect", "confirm", "book", "booked"]


async def test_a_failed_booking_goes_back_to_collecting():
    runner = make_runner(FakeClinic(booking_status=409))
    await runner.start()
    await runner.enter("confirm")

    await runner.enter("book")

    assert runner.current.id == "collect"
    assert not runner.ended
    assert "Latest result of book_appointment" in runner.system_prompt("base")


async def test_unreadable_answers_are_not_saved():
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")

    status = await runner.save_fields({"day": "whenever suits", "time": "11"})

    assert "Could not read day" in status
    assert runner.fields == {"time": "11:00"}


async def test_each_step_offers_only_its_own_tools_plus_global_moves():
    runner = make_runner()
    await runner.start()
    greet_tools = [tool.name for tool in runner.tools()]
    await runner.enter("collect")
    collect_tools = [tool.name for tool in runner.tools()]

    assert greet_tools == ["go_to_collect_booking_details", "go_to_transfer"]
    assert collect_tools == ["save_fields", "go_to_transfer", "check_availability"]


async def test_attached_tool_reads_day_words_like_an_answer():
    clinic = FakeClinic()
    runner = make_runner(clinic)
    await runner.start()
    await runner.enter("collect")
    check = next(tool for tool in runner.tools() if tool.name == "check_availability")

    result = await check.ainvoke({"day": "tomorrow"})

    assert clinic.requests[0].url.params["day"] == "2026-10-31"
    assert "11:30" in result


async def test_turn_that_moves_answers_from_the_new_step():
    runner = make_runner()
    await runner.start()
    model = ScriptedModel(
        script=[call("go_to_collect_booking_details"), AIMessage(content="May I have your name?")]
    )
    graph = FlowGraph(runner, model, "You are the receptionist.", max_retries=0)

    reply = await run_turn(graph, "I want to book")

    assert reply == "Sure. May I have your name?"
    assert runner.current.id == "collect"
    assert "Current step: Collect booking details" in model.seen[1][0].content
    assert model.bound[1][0] == "save_fields"


async def test_a_step_cannot_call_a_tool_that_is_not_attached_to_it():
    clinic = FakeClinic()
    runner = make_runner(clinic)
    await runner.start()
    model = ScriptedModel(
        script=[call("book_appointment"), AIMessage(content="How can I help you?")]
    )
    graph = FlowGraph(runner, model, "base", max_retries=0)

    await run_turn(graph, "Just book anything")

    tool_message = model.seen[1][-1]
    assert tool_message.content == "book_appointment is not available in this step."
    assert clinic.requests == []
    assert runner.current.id == "greet"


async def test_global_move_ends_with_the_transfer_message():
    runner = make_runner()
    await runner.start()
    graph = FlowGraph(runner, ScriptedModel(script=[call("go_to_transfer")]), "base", 0)

    reply = await run_turn(graph, "Let me talk to a person")

    assert reply == "Connecting you."
    assert runner.outcome == "transfer_requested"
    assert await run_turn(graph, "hello?") == ""


class FlakyModel(ScriptedModel):
    failures: int = 1

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        if self.failures:
            self.failures -= 1
            raise ConnectionError("dropped")
        from langchain_core.outputs import ChatGenerationChunk

        yield ChatGenerationChunk(message=AIMessageChunk(content=self.script.pop(0).content))


async def test_model_call_that_fails_before_speaking_is_retried():
    runner = make_runner()
    await runner.start()
    graph = FlowGraph(runner, FlakyModel(script=[AIMessage(content="Hello!")]), "base", 1)

    assert await run_turn(graph, "hi") == "Hello!"

    no_retry = FlowGraph(runner, FlakyModel(script=[AIMessage(content="x")]), "base", 0)
    with pytest.raises(ConnectionError):
        await run_turn(no_retry, "hi")


def graph_for(runner: FlowRunner, script: list[AIMessage]) -> tuple[FlowGraph, ScriptedModel]:
    model = ScriptedModel(script=script)
    return FlowGraph(runner, model, "base", max_retries=0, filler_delay_seconds=0.01), model


async def test_a_reply_written_with_save_fields_is_the_turns_only_model_call():
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")
    runner.entry_line = ""
    saved_and_asked = AIMessage(
        content="Thanks, Rohan. How old is the patient?",
        tool_calls=[{"name": "save_fields", "args": {"patient_name": "Rohan"}, "id": "c1"}],
    )
    graph, model = graph_for(runner, [saved_and_asked])

    reply = await run_turn(graph, "It's for Rohan")

    assert reply == "Thanks, Rohan. How old is the patient?"
    assert len(model.seen) == 1
    assert runner.fields["patient_name"] == "Rohan"


async def test_a_move_still_asks_the_new_step_after_saying_its_entry_line():
    runner = make_runner()
    await runner.start()
    graph, model = graph_for(
        runner, [call("go_to_collect_booking_details"), AIMessage(content="Your name?")]
    )

    reply = await run_turn(graph, "Book me in")

    assert reply == "Sure. Your name?"
    assert len(model.seen) == 2
    assert model.seen[1][-1].content == "Sure."


async def test_a_slow_tool_says_its_line_once_and_a_fast_one_stays_silent():
    slow = make_runner(FakeClinic(delay_seconds=0.1))
    fast = make_runner(FakeClinic())
    for runner in (slow, fast):
        await runner.start()
        await runner.enter("collect")
        runner.entry_line = ""
    checks = [call("check_availability", day="tomorrow"), AIMessage(content="11 or 11:30?")]
    slow_graph, _ = graph_for(slow, list(checks))
    fast_graph = FlowGraph(fast, ScriptedModel(script=list(checks)), "base", 0, 5.0)

    assert await run_turn(slow_graph, "Which times?") == "One moment. 11 or 11:30?"
    assert await run_turn(fast_graph, "Which times?") == "11 or 11:30?"


async def test_a_tool_result_fills_the_fields_it_is_mapped_to():
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")
    check = next(tool for tool in runner.tools() if tool.name == "check_availability")

    await check.ainvoke({"day": "Saturday"})

    assert runner.fields["day"] == "2026-10-31"


def test_value_at_follows_dot_paths_and_misses_return_none():
    data = {"booking": {"id": "A-1", "doctor": {"name": "Dr. Mehta"}}}

    assert value_at(data, "booking.doctor.name") == "Dr. Mehta"
    assert value_at(data, "booking.missing") is None
    assert value_at(data, "booking.id.deeper") is None
