"""The flow format. The console edits it, the API validates it, the runtime runs it."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from studio_api.database import UtcDateTime
from studio_api.flows.constants import FIELD_TYPES, HTTP_METHODS, IDENTIFIER_PATTERN

Identifier = Annotated[str, Field(pattern=IDENTIFIER_PATTERN, max_length=60)]


class Position(BaseModel):
    x: float = 0
    y: float = 0


class FieldSpec(BaseModel):
    name: Identifier
    type: Literal[FIELD_TYPES] = "text"
    description: str = ""
    required: bool = True


class StepData(BaseModel):
    name: str = "Step"
    instructions: str = ""
    fields: list[FieldSpec] = []
    # Ids of tool nodes the LLM may call while in this step; no others.
    tools: list[str] = []
    use_knowledge: bool = False
    # Spoken as soon as the flow arrives here, while the LLM writes the step's first reply;
    # {field} placeholders are filled in by code (a read-back never misstates a number).
    say_on_enter: str = ""
    # After saying the line, wait for the caller instead of asking the LLM for a reply.
    wait_after_enter: bool = False


class ToolData(BaseModel):
    name: Identifier = "call_api"
    description: str = ""
    method: Literal[HTTP_METHODS] = "GET"
    # {field} placeholders are filled from collected fields (or the LLM's arguments).
    url: str = ""
    body: dict[str, str] = {}
    # Spoken if the call is still running after a moment (empty: silent).
    say_while_running: str = ""
    # field name -> dot path in the JSON result, e.g. {"doctor": "doctor"}; copied on success.
    save_to_fields: dict[Identifier, str] = {}
    # Dot paths of the result the LLM is shown (empty: all of it); a shorter prompt is faster.
    result_fields: list[str] = []


class EndData(BaseModel):
    outcome: Identifier = "completed"
    # Spoken last; {placeholders} come from fields and the latest tool result.
    message: str = ""


class TransferData(BaseModel):
    message: str = ""
    destination: str = ""


class GlobalData(BaseModel):
    name: str = "Global"
    condition: str = ""


class NodeBase(BaseModel):
    id: str = Field(min_length=1, max_length=60)
    position: Position = Position()


class StartNode(NodeBase):
    type: Literal["start"]
    data: dict = {}


class StepNode(NodeBase):
    type: Literal["step"]
    data: StepData = StepData()


class ToolNode(NodeBase):
    type: Literal["tool"]
    data: ToolData = ToolData()


class EndNode(NodeBase):
    type: Literal["end"]
    data: EndData = EndData()


class TransferNode(NodeBase):
    type: Literal["transfer"]
    data: TransferData = TransferData()


class GlobalNode(NodeBase):
    type: Literal["global"]
    data: GlobalData = GlobalData()


FlowNode = Annotated[
    StartNode | StepNode | ToolNode | EndNode | TransferNode | GlobalNode,
    Field(discriminator="type"),
]


class FlowEdge(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    source: str
    target: str
    kind: Literal["condition", "fields_complete", "success", "failure", "always"] = "condition"
    condition: str = ""


class Flow(BaseModel):
    nodes: list[FlowNode] = []
    edges: list[FlowEdge] = []


class FlowIssue(BaseModel):
    message: str
    node_id: str | None = None
    edge_id: str | None = None


class FlowDraft(BaseModel):
    """The editable flow, with what must be fixed before it can be published."""

    flow: Flow | None
    issues: list[FlowIssue]
    published_version: int | None


class FlowVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    published_at: UtcDateTime
    node_count: int
