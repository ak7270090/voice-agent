"""The flow format as the runtime reads it. The API validates flows before they are published
(studio_api.flows); these models only parse what running a flow needs."""

from typing import Annotated, Literal

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


class ToolData(BaseModel):
    name: str
    description: str = ""
    method: str = "GET"
    url: str
    body: dict[str, str] = {}
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
