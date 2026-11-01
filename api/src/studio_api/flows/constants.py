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

# Tool kinds: any HTTP API, or a ready-made Cal.com call (free times; book) that answers in the
# same shape as the demo clinic, so a booking flow works with either.
HTTP_TOOL = "http"
CALCOM_AVAILABILITY_TOOL = "calcom_availability"
CALCOM_BOOKING_TOOL = "calcom_booking"
TOOL_KINDS = (HTTP_TOOL, CALCOM_AVAILABILITY_TOOL, CALCOM_BOOKING_TOOL)
CALCOM_TOOLS = (CALCOM_AVAILABILITY_TOOL, CALCOM_BOOKING_TOOL)
CALCOM_API_URL = "https://api.cal.com/v2"
# The fields a Cal.com tool reads, besides the resource (doctor) and the name it books under.
DAY_FIELD = "day"
TIME_FIELD = "time"
EMAIL_FIELD = "email"

IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]*$"
# {field} placeholders in tool URLs, headers, bodies and end messages.
PLACEHOLDER_PATTERN = r"\{([a-z][a-z0-9_]*)\}"
# {secret.NAME} in a tool's URL, headers or body: filled by the runtime from stored secrets,
# never shown to the LLM or written to the call record.
SECRET_PLACEHOLDER_PATTERN = r"\{secret\.([A-Z][A-Z0-9_]*)\}"
# Filled by the runtime before the first step, so tools can use them like fields (a phone
# call's number for a customer lookup; empty on browser test calls).
CALL_VALUES = ("caller_number",)
# A transfer goes to a phone number or a SIP address (sip:desk@pbx.example.com).
TRANSFER_DESTINATION_PATTERN = r"^(\+[1-9]\d{6,14}|sips?:\S+)$"
