"""A hospital receptionist. Its flow rebuilds clinic-voice-agent's booking form as nodes: collect,
check free times, read back, book, give the booking ID."""

from studio_backend.agent_catalog.template_parts import at, build_agent_fields, edge
from studio_backend.agents.schemas import AgentTemplate, AnalysisField
from studio_backend.config import Settings
from studio_backend.flows.constants import CALCOM_AVAILABILITY_TOOL, CALCOM_BOOKING_TOOL
from studio_backend.flows.schemas import (
    CalcomResource,
    CalcomSettings,
    EndData,
    EndNode,
    FieldSpec,
    Flow,
    GlobalData,
    GlobalNode,
    StartNode,
    StepData,
    StepNode,
    ToolData,
    ToolNode,
    TransferData,
    TransferNode,
)

CLINIC_BOOKING_INSTRUCTIONS = """You are the receptionist of City Hospital.
Help callers book, move or cancel an appointment, and answer questions about the hospital.
Be warm and brief."""

GREETING = "Welcome to City Hospital. How can I help you today?"
CLINIC_ANALYSIS = (
    [
        AnalysisField(
            name="reason",
            type="choice",
            description="Why the caller called",
            choices=["book", "question", "change", "other"],
        ),
        # A choice, not text: as text, "skin doctor" and "Dr. Priya Mehta" were both answers.
        AnalysisField(
            name="doctor",
            type="choice",
            description="The doctor the appointment or question was about",
            choices=["Dr. Anil Sharma", "Dr. Priya Mehta", "Dr. Ravi Iyer", "Dr. Sana Khan"],
        ),
        AnalysisField(
            name="asked_about_fees",
            type="yes_no",
            description="Did the caller ask what a visit costs?",
        ),
    ],
    "An appointment was booked (the agent gave a booking ID), or the caller's question was "
    "answered.",
)
# The demo clinic's doctors, as the agent names them when the caller has not said.
DOCTOR_LIST = (
    "Dr. Anil Sharma, general physician; Dr. Priya Mehta, skin; Dr. Ravi Iyer, children; "
    "Dr. Sana Khan, bones and joints"
)
# Each doctor, and the words a caller may use instead of the name.
CLINIC_DOCTORS = (
    (
        "Dr. Anil Sharma",
        ("general physician", "sharma", "general", "physician", "fever", "cold", "cough"),
    ),
    (
        "Dr. Priya Mehta",
        ("dermatologist", "mehta", "skin", "derma", "dermatologist", "rash", "acne", "hair"),
    ),
    (
        "Dr. Ravi Iyer",
        (
            "paediatrician",
            "iyer",
            "child",
            "kid",
            "baby",
            "paediatric",
            "pediatric",
            "paediatrician",
        ),
    ),
    (
        "Dr. Sana Khan",
        ("orthopaedic surgeon", "khan", "bone", "joint", "ortho", "knee", "back", "fracture"),
    ),
)


def calcom_clinic_settings() -> CalcomSettings:
    """The demo clinic's doctors as Cal.com resources; each event type ID is set by the user
    (it is their own Cal.com account), so a new agent shows that as an issue to fix."""
    return CalcomSettings(
        api_key_secret="CALCOM_KEY",
        resources=[
            CalcomResource(name=name, keywords=list(keywords)) for name, keywords in CLINIC_DOCTORS
        ],
    )


def availability_tool(clinic_api_url: str, calcom: CalcomSettings | None) -> ToolData:
    common = {
        "name": "check_availability",
        "description": "Free times for a doctor (name or speciality) on a day (YYYY-MM-DD).",
        "say_while_running": "One moment, let me check.",
        # The clinic's own spelling, and the day it checked (a new day the caller picked
        # replaces the old one).
        "save_to_fields": {"doctor": "doctor", "day": "day"},
        "result_fields": ["doctor", "weekday", "free_times", "next_open_days"],
    }
    if calcom is not None:
        return ToolData(kind=CALCOM_AVAILABILITY_TOOL, calcom=calcom, **common)
    return ToolData(url=f"{clinic_api_url}/availability?doctor={{doctor}}&day={{day}}", **common)


def booking_tool(clinic_api_url: str, calcom: CalcomSettings | None) -> ToolData:
    common = {
        "name": "book_appointment",
        "description": "Books the appointment and returns the booking ID.",
        # Cal.com took 2.4 s to book on a live run; silence that long sounds like a dead line.
        "say_while_running": "One moment while I book that.",
    }
    if calcom is not None:
        return ToolData(kind=CALCOM_BOOKING_TOOL, calcom=calcom, **common)
    return ToolData(
        method="POST",
        url=f"{clinic_api_url}/appointments",
        body={
            "patient_name": "{patient_name}",
            "patient_age": "{patient_age}",
            "doctor": "{doctor}",
            "day": "{day}",
            "time": "{time}",
        },
        **common,
    )


def build_clinic_booking_flow(clinic_api_url: str, calcom: CalcomSettings | None = None) -> Flow:
    """Books through the demo clinic's API, or into Cal.com when `calcom` is given."""
    nodes = [
        StartNode(id="start", type="start", position=at(1, 0)),
        StepNode(
            id="greet",
            type="step",
            position=at(1, 1),
            data=StepData(
                name="Find out what the caller wants",
                instructions="Ask how you can help: booking an appointment or a question.",
            ),
        ),
        StepNode(
            id="collect",
            type="step",
            position=at(0, 2),
            data=StepData(
                name="Collect booking details",
                instructions=(
                    "Save every detail the caller has already given in this call, then ask for "
                    "one missing detail at a time. If the caller has not said which doctor or "
                    "what the problem is, ask, and name the doctors: "
                    + DOCTOR_LIST
                    + ". Do not ask for a time yet: the free times are checked next. If you "
                    "are back here because no doctor matched, say so and ask again."
                ),
                fields=[
                    FieldSpec(name="patient_name", type="name", description="Patient's full name"),
                    FieldSpec(name="patient_age", type="number", description="Patient's age"),
                    FieldSpec(
                        name="doctor",
                        description=(
                            "Which doctor: a name, speciality or health problem, e.g. Dr. "
                            "Mehta, skin, skin doctor, fever. 'A doctor appointment' alone does "
                            "not say which"
                        ),
                    ),
                    FieldSpec(name="day", type="date", description="Day of the appointment"),
                ],
                say_on_enter="Sure, I can help with that.",
            ),
        ),
        StepNode(
            id="choose_time",
            type="step",
            position=at(-1, 3),
            data=StepData(
                name="Choose a free time",
                instructions=(
                    "Offer only times from the latest check_availability result, a few at a "
                    "time, said the way people say them (13:30 is half past one); never "
                    "suggest any other time. If the day has none, offer its next "
                    "open days, and when the caller picks another day, call check_availability "
                    "for it. If you are back here because the booking failed, call "
                    "check_availability again and offer the new free times."
                ),
                fields=[
                    FieldSpec(
                        name="time",
                        type="time",
                        description="One of the free times the caller chose",
                    ),
                ],
                tools=["check_availability"],
            ),
        ),
        StepNode(
            id="questions",
            type="step",
            position=at(2, 2),
            data=StepData(
                name="Answer questions",
                instructions="Answer questions about the hospital from its documents.",
                use_knowledge=True,
            ),
        ),
        StepNode(
            id="confirm",
            type="step",
            position=at(0, 3),
            data=StepData(
                name="Read back and confirm",
                instructions=(
                    "The details were just read back to the caller. If they say something is "
                    "wrong, ask what to change."
                ),
                # Filled in by code from the collected fields, so names, ages, dates and times
                # are said exactly; then the agent waits for the caller's answer.
                say_on_enter=(
                    "To confirm: {patient_name}, aged {patient_age}, with {doctor} on {day} at "
                    "{time}. Is that right?"
                ),
                wait_after_enter=True,
            ),
        ),
        ToolNode(
            id="check_availability",
            type="tool",
            position=at(-1, 2),
            data=availability_tool(clinic_api_url, calcom),
        ),
        ToolNode(
            id="book",
            type="tool",
            position=at(0, 4),
            data=booking_tool(clinic_api_url, calcom),
        ),
        EndNode(
            id="booked",
            type="end",
            position=at(0, 5),
            data=EndData(
                outcome="booked",
                message=(
                    "Your appointment with {doctor} is booked for {weekday} at {time}. "
                    "Your booking ID is {booking_id}. Thank you for calling."
                ),
            ),
        ),
        EndNode(
            id="goodbye",
            type="end",
            position=at(2, 3),
            data=EndData(outcome="answered", message="Thank you for calling City Hospital."),
        ),
        GlobalNode(
            id="wants_human",
            type="global",
            position=at(3, 0),
            data=GlobalData(name="Wants a person", condition="The caller asks for a human"),
        ),
        TransferNode(
            id="front_desk",
            type="transfer",
            position=at(3, 1),
            data=TransferData(message="Let me connect you to our front desk."),
        ),
    ]
    edges = [
        edge("start", "greet", "always"),
        edge("greet", "collect", condition="The caller wants to book an appointment"),
        edge("greet", "questions", condition="The caller has a question about the hospital"),
        edge("questions", "collect", condition="The caller wants to book an appointment"),
        edge("questions", "goodbye", condition="The caller has no more questions"),
        # The free times are checked by code once the doctor and day are known, so a time is
        # only ever chosen from them (the LLM once skipped the check and made up 12:00).
        edge("collect", "check_availability", "fields_complete"),
        edge("check_availability", "choose_time", "success"),
        edge("check_availability", "collect", "failure"),
        edge("choose_time", "confirm", "fields_complete"),
        edge("confirm", "book", condition="The caller confirms the details are right"),
        edge("confirm", "choose_time", condition="The caller wants a different time or day"),
        edge(
            "confirm",
            "collect",
            condition="The caller wants to change the name, age or doctor",
        ),
        edge("book", "booked", "success"),
        edge("book", "choose_time", "failure"),
        edge("wants_human", "front_desk", "always"),
    ]
    return Flow(nodes=nodes, edges=edges)


def build_templates(settings: Settings) -> list[AgentTemplate]:
    return [
        AgentTemplate(
            id="clinic-booking",
            name="Clinic booking",
            summary="Books, moves and cancels appointments; answers from hospital documents.",
            channel_label="Inbound",
            fields=build_agent_fields(
                settings,
                "Clinic receptionist",
                CLINIC_BOOKING_INSTRUCTIONS,
                GREETING,
                CLINIC_ANALYSIS,
            ),
            flow=build_clinic_booking_flow(settings.demo_clinic_api_url),
        ),
        AgentTemplate(
            id="clinic-booking-calcom",
            name="Clinic booking (Cal.com)",
            summary="Books into each doctor's Cal.com calendar: save your Cal.com key as "
            "CALCOM_KEY, then set each doctor's event type.",
            channel_label="Inbound",
            fields=build_agent_fields(
                settings,
                "Clinic receptionist (Cal.com)",
                CLINIC_BOOKING_INSTRUCTIONS,
                GREETING,
                CLINIC_ANALYSIS,
            ),
            flow=build_clinic_booking_flow(
                settings.demo_clinic_api_url, calcom=calcom_clinic_settings()
            ),
        ),
    ]
