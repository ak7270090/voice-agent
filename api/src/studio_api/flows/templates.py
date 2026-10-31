"""Ready-made flows for the agent templates. The clinic one rebuilds clinic-voice-agent's
booking form as nodes: collect, check free times, read back, book, give the booking ID."""

from studio_api.flows.schemas import (
    EndData,
    EndNode,
    FieldSpec,
    Flow,
    FlowEdge,
    GlobalData,
    GlobalNode,
    Position,
    StartNode,
    StepData,
    StepNode,
    ToolData,
    ToolNode,
    TransferData,
    TransferNode,
)

COLUMN = 300
ROW = 150
# The demo clinic's doctors, as the agent names them when the caller has not said.
DOCTOR_LIST = (
    "Dr. Anil Sharma, general physician; Dr. Priya Mehta, skin; Dr. Ravi Iyer, children; "
    "Dr. Sana Khan, bones and joints"
)


def at(column: float, row: float) -> Position:
    return Position(x=column * COLUMN, y=row * ROW)


def edge(source: str, target: str, kind: str = "condition", condition: str = "") -> FlowEdge:
    return FlowEdge(
        id=f"{source}-{target}", source=source, target=target, kind=kind, condition=condition
    )


def build_clinic_booking_flow(clinic_api_url: str) -> Flow:
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
            data=ToolData(
                name="check_availability",
                description="Free times for a doctor (name or speciality) on a day (YYYY-MM-DD).",
                url=f"{clinic_api_url}/demo-clinic/availability?doctor={{doctor}}&day={{day}}",
                say_while_running="One moment, let me check.",
                # The clinic's own spelling, and the day it checked (a new day the caller
                # picked replaces the old one).
                save_to_fields={"doctor": "doctor", "day": "day"},
                result_fields=["doctor", "weekday", "free_times", "next_open_days"],
            ),
        ),
        ToolNode(
            id="book",
            type="tool",
            position=at(0, 4),
            data=ToolData(
                name="book_appointment",
                description="Books the appointment and returns the booking ID.",
                method="POST",
                url=f"{clinic_api_url}/demo-clinic/appointments",
                body={
                    "patient_name": "{patient_name}",
                    "patient_age": "{patient_age}",
                    "doctor": "{doctor}",
                    "day": "{day}",
                    "time": "{time}",
                },
            ),
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


def build_reminder_flow() -> Flow:
    nodes = [
        StartNode(id="start", type="start", position=at(1, 0)),
        StepNode(
            id="remind",
            type="step",
            position=at(1, 1),
            data=StepData(
                name="Confirm the appointment",
                instructions=(
                    "Remind the patient of tomorrow's appointment and ask if they will come."
                ),
            ),
        ),
        EndNode(
            id="confirmed",
            type="end",
            position=at(0, 2),
            data=EndData(outcome="confirmed", message="Great, see you tomorrow. Goodbye."),
        ),
        EndNode(
            id="reschedule",
            type="end",
            position=at(2, 2),
            data=EndData(
                outcome="reschedule_requested",
                message="No problem. The front desk will call you to find a new time. Goodbye.",
            ),
        ),
        EndNode(
            id="opted_out",
            type="end",
            position=at(3, 2),
            # A campaign never calls a contact again after this outcome.
            data=EndData(
                outcome="opted_out",
                message="Understood, we won't call you again. Goodbye.",
            ),
        ),
    ]
    edges = [
        edge("start", "remind", "always"),
        edge("remind", "confirmed", condition="The patient will come"),
        edge("remind", "reschedule", condition="The patient cannot come or wants another time"),
        edge("remind", "opted_out", condition="The person asks not to be called again"),
    ]
    return Flow(nodes=nodes, edges=edges)


def build_lead_qualifier_flow() -> Flow:
    nodes = [
        StartNode(id="start", type="start", position=at(1, 0)),
        StepNode(
            id="qualify",
            type="step",
            position=at(1, 1),
            data=StepData(
                name="Qualify the lead",
                instructions="Find out what they need, their budget and when they want to start.",
                fields=[
                    FieldSpec(name="need", description="What they want to solve"),
                    FieldSpec(name="budget", description="Budget, with currency"),
                    FieldSpec(name="timeline", description="When they want to start"),
                ],
            ),
        ),
        StepNode(
            id="offer_meeting",
            type="step",
            position=at(1, 2),
            data=StepData(
                name="Offer a meeting",
                instructions="Offer a short call with sales and ask for a day that suits them.",
                fields=[FieldSpec(name="meeting_day", type="date", description="Meeting day")],
            ),
        ),
        EndNode(
            id="qualified",
            type="end",
            position=at(0, 3),
            data=EndData(
                outcome="meeting_requested",
                message="Thanks. Our sales team will confirm the meeting for {meeting_day}.",
            ),
        ),
        EndNode(
            id="not_interested",
            type="end",
            position=at(2, 3),
            data=EndData(outcome="not_interested", message="Thanks for your time. Goodbye."),
        ),
    ]
    edges = [
        edge("start", "qualify", "always"),
        edge("qualify", "offer_meeting", "fields_complete"),
        edge("qualify", "not_interested", condition="They are not interested"),
        edge("offer_meeting", "qualified", "fields_complete"),
        edge("offer_meeting", "not_interested", condition="They do not want a meeting"),
    ]
    return Flow(nodes=nodes, edges=edges)
