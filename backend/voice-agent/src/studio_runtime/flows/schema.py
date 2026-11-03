"""The flow format as the runtime reads it. The API validates flows before they are published
(studio_api.flows); these models only parse what running a flow needs."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class FieldSpec(BaseModel):
    name: str
    type: str = "text"
    description: str = ""
    required: bool = True


class StepData(BaseModel):
    name: str = "Step"
    instructions: str = ""
    fields: list[FieldSpec] = []
    tools: list[str] = []
    use_knowledge: bool = False
    say_on_enter: str = ""
    wait_after_enter: bool = False


class CalcomResource(BaseModel):
    name: str
    event_type_id: int | None = None
    keywords: list[str] = []


class CalcomSettings(BaseModel):
    api_key_secret: str = ""
    time_zone: str = "Asia/Kolkata"
    resources: list[CalcomResource] = []
    resource_field: str = "doctor"
    name_field: str = "patient_name"
    # Empty: the Cal.com account's own email.
    attendee_email: str = ""
    api_url: str = "https://api.cal.com/v2"


class ToolData(BaseModel):
    kind: str = "http"
    name: str
    description: str = ""
    calcom: CalcomSettings | None = None
    method: str = "GET"
    url: str = ""
    headers: dict[str, str] = {}
    body: dict[str, Any] = {}
    say_while_running: str = ""
    save_to_fields: dict[str, str] = {}
    result_fields: list[str] = []


class EndData(BaseModel):
    outcome: str = "completed"
    message: str = ""


class TransferData(BaseModel):
    message: str = ""
    destination: str = ""


class GlobalData(BaseModel):
    name: str = "Global"
    condition: str = ""


class StartNode(BaseModel):
    id: str
    type: Literal["start"]


class StepNode(BaseModel):
    id: str
    type: Literal["step"]
    data: StepData


class ToolNode(BaseModel):
    id: str
    type: Literal["tool"]
    data: ToolData


class EndNode(BaseModel):
    id: str
    type: Literal["end"]
    data: EndData


class TransferNode(BaseModel):
    id: str
    type: Literal["transfer"]
    data: TransferData


class GlobalNode(BaseModel):
    id: str
    type: Literal["global"]
    data: GlobalData


FlowNode = Annotated[
    StartNode | StepNode | ToolNode | EndNode | TransferNode | GlobalNode,
    Field(discriminator="type"),
]


class FlowEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str = "condition"
    condition: str = ""


class Flow(BaseModel):
    nodes: list[FlowNode]
    edges: list[FlowEdge]
