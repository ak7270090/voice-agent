import pytest
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from studio_api.agents.schemas import AnalysisField
from studio_api.calls.analysis import result_model, run_analysis
from tests.test_agents import create_agent
from tests.test_call_records import SPOKEN, end, start

FIELDS = [
    {"name": "doctor", "type": "text", "description": "Which doctor the caller wanted"},
    {
        "name": "visit_type",
        "type": "choice",
        "description": "Why they are coming",
        "choices": ["new", "follow_up"],
    },
    {"name": "asked_about_fees", "type": "yes_no", "description": "Did they ask about fees?"},
    {"name": "patient_age", "type": "number", "description": "The patient's age"},
]
GOOD_ANSWER = {
    "summary": "Asha wanted a skin doctor. She was booked for Monday at 11:00.",
    "successful": True,
    "success_reason": "A booking was made.",
    "sentiment": "positive",
    "fields": {
        "doctor": "Dr. Priya Mehta",
        "visit_type": "new",
        "asked_about_fees": False,
        "patient_age": 34,
    },
    "qa_score": 5,
    "qa_notes": "No issues",
}


def test_every_analysis_field_is_required_but_may_be_null():
    shape = result_model([AnalysisField.model_validate(field) for field in FIELDS])
    with_nulls = {**GOOD_ANSWER, "fields": dict.fromkeys(GOOD_ANSWER["fields"])}
    missing_one = {**GOOD_ANSWER, "fields": {"doctor": "Dr. Mehta"}}

    assert shape.model_validate(with_nulls).fields.doctor is None
    with pytest.raises(ValidationError):
        shape.model_validate(missing_one)


def test_a_choice_answer_must_be_one_of_its_choices():
    shape = result_model([AnalysisField.model_validate(field) for field in FIELDS])
    off_list = {**GOOD_ANSWER, "fields": {**GOOD_ANSWER["fields"], "visit_type": "emergency"}}

    with pytest.raises(ValidationError):
        shape.model_validate(off_list)


@pytest.mark.parametrize(
    "field",
    [
        {"name": "visit_type", "type": "choice", "description": "Why"},
        {"name": "doctor", "type": "text", "description": "Who", "choices": ["a"]},
        {"name": "Bad Name", "type": "text", "description": "Who"},
    ],
)
async def test_an_agent_rejects_analysis_fields_that_cannot_work(client, field):
    agent = await create_agent(client)

    response = await client.patch(f"/agents/{agent['id']}", json={"analysis_fields": [field]})

    assert response.status_code == 422


def fake_model(answer: dict, seen: list):
    """Stands in for the LLM: records the prompt and answers in the requested shape."""

    def factory(settings, shape):
        def respond(messages):
            seen.append(messages)
            return shape.model_validate(answer)

        return RunnableLambda(respond)

    return factory


async def analysed_call(client, runtime_headers, factory, **agent_changes) -> dict:
    agent = await create_agent(client, analysis_fields=FIELDS, **agent_changes)
    call_id = await start(client, runtime_headers, agent["id"], "web-1")
    await end(client, runtime_headers, call_id, transcript=SPOKEN, outcome="booked")
    await run_analysis(client.app.state.session_factory, None, call_id, factory)
    return (await client.get(f"/calls/{call_id}")).json()


async def test_the_analysis_is_saved_with_the_agents_fields_and_success_rule(
    client, runtime_headers
):
    seen: list = []

    call = await analysed_call(
        client,
        runtime_headers,
        fake_model(GOOD_ANSWER, seen),
        success_rule="A booking was made",
    )

    system, transcript = seen[0]
    assert call["analysis_status"] == "done"
    assert call["analysis"]["fields"]["doctor"] == "Dr. Priya Mehta"
    assert call["analysis"]["successful"] is True
    assert "A booking was made" in system.content
    assert "user: Book me in please." in transcript.content
    assert "Outcome recorded by the flow: booked" in transcript.content


async def test_an_analysis_that_fails_is_marked_failed_not_retried_forever(client, runtime_headers):
    def broken(settings, shape):
        def respond(messages):
            raise TimeoutError("model timed out")

        return RunnableLambda(respond)

    call = await analysed_call(client, runtime_headers, broken)

    assert call["analysis_status"] == "failed"
    assert call["analysis"] == {}


async def test_an_analysed_call_is_not_analysed_again(client, runtime_headers):
    seen: list = []
    call = await analysed_call(client, runtime_headers, fake_model(GOOD_ANSWER, seen))

    await run_analysis(
        client.app.state.session_factory, None, call["id"], fake_model(GOOD_ANSWER, seen)
    )

    assert len(seen) == 1
