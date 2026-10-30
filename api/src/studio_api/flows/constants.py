START_NODE = "start"
STEP_NODE = "step"
TOOL_NODE = "tool"
END_NODE = "end"
TRANSFER_NODE = "transfer"
GLOBAL_NODE = "global"

# Edge kinds. A condition is decided by the LLM; the others by code.
CONDITION_EDGE = "condition"
FIELDS_COMPLETE_EDGE = "fields_complete"
SUCCESS_EDGE = "success"
FAILURE_EDGE = "failure"
ALWAYS_EDGE = "always"

ALLOWED_EDGE_KINDS = {
    START_NODE: {ALWAYS_EDGE},
    GLOBAL_NODE: {ALWAYS_EDGE},
    STEP_NODE: {CONDITION_EDGE, FIELDS_COMPLETE_EDGE},
    TOOL_NODE: {SUCCESS_EDGE, FAILURE_EDGE, ALWAYS_EDGE},
    END_NODE: set(),
    TRANSFER_NODE: set(),
}

FIELD_TYPES = ("text", "name", "number", "date", "time", "yes_no", "phone")
HTTP_METHODS = ("GET", "POST")

IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]*$"
# {field} placeholders in tool URLs, bodies and end messages.
PLACEHOLDER_PATTERN = r"\{([a-z][a-z0-9_]*)\}"
