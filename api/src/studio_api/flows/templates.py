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
                    "Ask for one missing detail at a time. As soon as you know the doctor (or "
                    "the problem) and the day, call check_availability and offer only the free "
                    "times it returns. If the day has none, offer the next open days."
                ),
                fields=[
                    FieldSpec(name="patient_name", type="name", description="Patient's full name"),
                    FieldSpec(name="patient_age", type="number", description="Patient's age"),
                    FieldSpec(
                        name="doctor",
                        description="Doctor's name, or the speciality or problem (e.g. skin)",
                    ),
                    FieldSpec(name="day", type="date", description="Day of the appointment"),
                    FieldSpec(name="time", type="time", description="A free time on that day"),
                ],
                tools=["check_availability"],
                say_on_enter="Sure, I can help with that.",
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
                    "In one sentence, read back all five details: the patient's name, their age, "
                    "the doctor, the day and the time. Then ask the caller to confirm."
                ),
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
                save_to_fields={"doctor": "doctor"},
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
        edge("collect", "confirm", "fields_complete"),
        edge("confirm", "book", condition="The caller confirms the details are right"),
        edge("confirm", "collect", condition="The caller wants to change a detail"),
        edge("book", "booked", "success"),
        edge("book", "collect", "failure"),
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
    ]
    edges = [
        edge("start", "remind", "always"),
        edge("remind", "confirmed", condition="The patient will come"),
        edge("remind", "reschedule", condition="The patient cannot come or wants another time"),
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
