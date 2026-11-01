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
from studio_runtime.observability import LlmCallTracer
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
        {
            "id": "confirm",
            "type": "step",
            "data": {
                "name": "Confirm",
                "say_on_enter": "Confirm: {patient_name}, {day} at {time}?",
                "wait_after_enter": True,
            },
        },
        {
            "id": "check",
            "type": "tool",
            "data": {
                "name": "check_availability",
                "url": CLINIC + "/availability?day={day}",
                "say_while_running": "One moment.",
                "save_to_fields": {"day": "day"},
                "result_fields": ["free_times"],
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
        {
            "id": "desk",
            "type": "transfer",
            "data": {"message": "Connecting you.", "destination": "+914412345678"},
        },
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


TOOL_UNAVAILABLE_LINE = "Sorry, I can't check that right now."


class FakeClinic:
    def __init__(
        self,
        booking_status: int = 201,
        delay_seconds: float = 0,
        down_lookups: int = 0,
        down_bookings: int = 0,
    ) -> None:
        self.requests: list[httpx.Request] = []
        self.booking_status = booking_status
        self.delay_seconds = delay_seconds
        # How many lookups or bookings get 503 before the clinic answers again.
        self.down_lookups = down_lookups
        self.down_bookings = down_bookings
        self.request_seen = asyncio.Event()

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.request_seen.set()
        await asyncio.sleep(self.delay_seconds)
        if request.url.path == "/availability":
            if self.down_lookups:
                self.down_lookups -= 1
                return httpx.Response(503, text="unavailable")
            day = request.url.params["day"]
            return httpx.Response(200, json={"free_times": ["11:00", "11:30"], "day": day})
        if self.down_bookings:
            self.down_bookings -= 1
            return httpx.Response(503, text="unavailable")
        return httpx.Response(self.booking_status, json={"booking_id": "A-1001"})


def make_runner(clinic: FakeClinic | None = None, idempotency_prefix: str = "") -> FlowRunner:
    http = httpx.AsyncClient(transport=httpx.MockTransport(clinic or FakeClinic()))
    return FlowRunner(
        Flow.model_validate(FLOW),
        http,
        parsers_for("en"),
        FRIDAY,
        tool_unavailable_line=TOOL_UNAVAILABLE_LINE,
        idempotency_prefix=idempotency_prefix,
    )


async def ready_to_book(runner: FlowRunner) -> None:
    await runner.start()
    runner.fields.update(
        {"patient_name": "Rohan", "patient_age": 34, "day": "2026-10-31", "time": "11:00"}
    )
    await runner.enter("confirm")


class ScriptedModel(BaseChatModel):
    """Replies with the scripted messages in order and remembers what it was shown."""

    script: list[AIMessage]
    seen: list[list] = []
    bound: list[list[str]] = []
    tool_choices: list[str | None] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        self.bound.append([tool.name for tool in tools])
        self.tool_choices.append(kwargs.get("tool_choice"))
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


async def test_every_tool_call_is_logged_with_who_asked_and_how_it_went():
    runner = make_runner(FakeClinic())
    await runner.start()
    await runner.enter("collect")
    await runner.save_fields(
        {"patient_name": "Rohan Gupta", "patient_age": "34", "day": "Saturday", "time": "11"}
    )
    await next(t for t in runner.tools() if t.description == "Caller confirms").ainvoke({})

    (booking,) = runner.tool_calls

    assert booking["name"] == "book_appointment"
    assert booking["by"] == "flow"
    assert booking["ok"] and not booking["unavailable"]
    assert '"booking_id": "A-1001"' in booking["result"]
    assert booking["ms"] >= 0 and booking["at"] > 0


async def test_a_failed_booking_goes_back_to_collecting():
    runner = make_runner(FakeClinic(booking_status=409))
    await runner.start()
    await runner.enter("confirm")

    await runner.enter("book")

    assert runner.current.id == "collect"
    assert not runner.ended
    assert "Latest result of book_appointment" in runner.system_prompt("base")


async def test_back_after_a_failed_booking_the_step_waits_for_the_caller():
    runner = make_runner(FakeClinic(booking_status=409))
    await ready_to_book(runner)

    await runner.enter("book")
    resaved = await runner.save_fields({"time": "11"})

    assert runner.entry_line == ""
    assert "book_appointment just failed" in runner.system_prompt("base")
    assert runner.current.id == "collect" and "Moved on" not in resaved

    await runner.take_answer("Then 11:30 please")
    await runner.save_fields({"time": "11:30"})
    assert runner.current.id == "confirm"


async def test_back_to_change_a_detail_the_step_asks_instead_of_reading_back_again():
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")
    await runner.save_fields(
        {"patient_name": "Rohan", "patient_age": "34", "day": "Saturday", "time": "11"}
    )
    change = next(t for t in runner.tools() if t.description == "Caller changes a detail")

    await change.ainvoke({})
    resaved = await runner.save_fields({"time": "11"})

    assert runner.current.id == "collect" and runner.entry_line == ""
    assert "came back to this step to change something" in runner.system_prompt("base")
    assert "Moved on" not in resaved

    await runner.take_answer("12 please")
    await runner.save_fields({"time": "12"})
    assert runner.current.id == "confirm"
    assert runner.entry_line == "Confirm: Rohan, Saturday 31 October at 12:00?"


async def test_a_pass_that_only_saved_without_words_makes_the_next_one_speak():
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")
    runner.entry_line = ""
    saved_silently = AIMessage(
        content="",
        tool_calls=[{"name": "save_fields", "args": {"patient_name": "Rohan"}, "id": "c1"}],
    )
    graph, model = graph_for(runner, [saved_silently, AIMessage(content="How old are you?")])

    reply = await run_turn(graph, "I'm Rohan")

    assert reply == "How old are you?"
    assert model.tool_choices == [None, "none"]


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
    assert runner.transfer_to == "+914412345678"
    assert await run_turn(graph, "hello?") == "Connecting you."


async def test_call_values_are_known_before_the_first_step_and_fill_tool_urls():
    lookups: list[str] = []

    def crm(request: httpx.Request) -> httpx.Response:
        lookups.append(str(request.url))
        return httpx.Response(200, json={"name": "Rohan"})

    flow = {
        "nodes": [
            {"id": "start", "type": "start"},
            {
                "id": "who",
                "type": "tool",
                "data": {"name": "who", "url": "https://crm.example/c?phone={caller_number}"},
            },
            {"id": "done", "type": "end", "data": {"message": "Hello {name}."}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "who", "kind": "always"},
            {"id": "e2", "source": "who", "target": "done", "kind": "success"},
        ],
    }
    runner = FlowRunner(
        Flow.model_validate(flow),
        httpx.AsyncClient(transport=httpx.MockTransport(crm)),
        parsers_for("en"),
        FRIDAY,
        call_values={"caller_number": "+919876543210"},
    )

    await runner.start()

    assert lookups == ["https://crm.example/c?phone=%2B919876543210"]
    assert runner.final_message == "Hello Rohan."
    assert runner.fields["caller_number"] == "+919876543210"


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


async def test_a_lookup_without_an_answer_is_tried_once_more():
    clinic = FakeClinic(down_lookups=1)
    runner = make_runner(clinic)
    await runner.start()
    await runner.enter("collect")
    check = next(tool for tool in runner.tools() if tool.name == "check_availability")

    result = await check.ainvoke({"day": "Saturday"})

    assert len(clinic.requests) == 2
    assert "11:30" in result


async def test_a_tool_that_stays_unavailable_gets_a_fixed_apology_and_no_guess():
    runner = make_runner(FakeClinic(down_lookups=2))
    await runner.start()
    await runner.enter("collect")
    runner.entry_line = ""
    graph, model = graph_for(
        runner,
        [call("check_availability", day="Saturday"), AIMessage(content="Shall I try again?")],
    )

    reply = await run_turn(graph, "What times are free?")

    assert reply == f"One moment. {TOOL_UNAVAILABLE_LINE} Shall I try again?"
    assert "Never guess" in model.seen[1][-1].content


async def test_a_booking_without_an_idempotency_key_is_not_sent_twice():
    clinic = FakeClinic(booking_status=502)
    runner = make_runner(clinic)
    await ready_to_book(runner)

    await runner.enter("book")

    assert len(clinic.requests) == 1
    assert runner.current.id == "collect"


async def test_a_booking_with_a_key_is_retried_safely_with_the_same_key():
    clinic = FakeClinic(down_bookings=1)
    runner = make_runner(clinic, idempotency_prefix="web-3f9a")
    await ready_to_book(runner)

    await runner.enter("book")

    keys = [request.headers["Idempotency-Key"] for request in clinic.requests]
    assert keys == ["web-3f9a:book", "web-3f9a:book"]
    assert runner.outcome == "booked"


async def test_a_booking_finishes_when_the_caller_cuts_in_and_its_message_is_said_next():
    clinic = FakeClinic(delay_seconds=0.2)
    runner = make_runner(clinic)
    await ready_to_book(runner)
    graph, _ = graph_for(runner, [call("go_to_book_appointment")])

    turn = asyncio.ensure_future(run_turn(graph, "Yes, that's right"))
    await clinic.request_seen.wait()
    turn.cancel()
    await asyncio.sleep(0.4)

    assert len(clinic.requests) == 1
    assert runner.outcome == "booked"
    assert await run_turn(graph, "Wait, is it booked?") == "Booked: A-1001."


async def test_a_timeout_counts_as_no_answer():
    async def times_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(times_out))
    runner = FlowRunner(Flow.model_validate(FLOW), http, parsers_for("en"), FRIDAY)
    await runner.start()
    await runner.enter("collect")
    check = next(tool for tool in runner.tools() if tool.name == "check_availability")

    result = await check.ainvoke({"day": "Saturday"})

    assert "got no answer" in result


async def test_a_read_back_is_filled_in_by_code_and_then_waits_for_the_caller():
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")
    runner.fields.update({"patient_name": "Rohan", "patient_age": 34, "day": "2026-10-31"})
    graph, model = graph_for(runner, [])

    reply = await run_turn(graph, "11 am works")

    assert reply == "Confirm: Rohan, Saturday 31 October at 11:00? "
    assert runner.current.id == "confirm"
    assert model.seen == []


async def test_two_lookups_in_one_message_run_together():
    clinic = FakeClinic(delay_seconds=0.3)
    runner = make_runner(clinic)
    await runner.start()
    await runner.enter("collect")
    runner.entry_line = ""
    both = AIMessage(
        content="",
        tool_calls=[
            {"name": "check_availability", "args": {"day": "Saturday"}, "id": "c1"},
            {"name": "check_availability", "args": {"day": "Monday"}, "id": "c2"},
        ],
    )
    graph = FlowGraph(runner, ScriptedModel(script=[both, AIMessage(content="Both work.")]), "b", 0)

    started = asyncio.get_running_loop().time()
    await run_turn(graph, "Saturday or Monday?")
    elapsed = asyncio.get_running_loop().time() - started

    assert len(clinic.requests) == 2
    assert elapsed < 0.55


async def test_the_llm_sees_only_the_result_fields_the_tool_names():
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")
    check = next(tool for tool in runner.tools() if tool.name == "check_availability")

    result = await check.ainvoke({"day": "Saturday"})

    assert json.loads(result) == {"free_times": ["11:00", "11:30"]}
    assert '"day"' not in runner.system_prompt("base").split("Latest result")[1]
    assert runner.fields["day"] == "2026-10-31"


async def test_a_turn_traces_its_tool_calls_moves_and_saved_fields(spans):
    runner = make_runner()
    await runner.start()
    await runner.enter("collect")
    runner.entry_line = ""
    model = ScriptedModel(
        script=[call("check_availability", day="tomorrow"), AIMessage(content="11 or 11:30?")]
    )
    graph = FlowGraph(runner, model, "base", max_retries=0, callbacks=[LlmCallTracer()])

    await run_turn(graph, "Which times?")
    await runner.save_fields({"patient_name": "Rohan", "patient_age": "34", "time": "11"})

    finished = spans.get_finished_spans()
    tool = next(span for span in finished if span.name == "check_availability")
    llm_call = next(span for span in finished if span.name == "llm_call")
    last_move = [span for span in finished if span.name == "flow.move"][-1]
    assert tool.attributes["langfuse.observation.type"] == "tool"
    assert '"day": "tomorrow"' in tool.attributes["langfuse.observation.input"]
    assert "11:30" in tool.attributes["langfuse.observation.output"]
    assert llm_call.attributes["flow.step"] == "collect"
    assert '"moved_by": "code"' in last_move.attributes["langfuse.observation.input"]
    assert '"to": "confirm"' in last_move.attributes["langfuse.observation.output"]
    assert any(span.name == "flow.save_fields" for span in finished)


def test_value_at_follows_dot_paths_and_misses_return_none():
    data = {"booking": {"id": "A-1", "doctor": {"name": "Dr. Mehta"}}}

    assert value_at(data, "booking.doctor.name") == "Dr. Mehta"
    assert value_at(data, "booking.missing") is None
    assert value_at(data, "booking.id.deeper") is None
