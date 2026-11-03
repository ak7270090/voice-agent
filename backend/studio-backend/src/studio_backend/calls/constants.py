ACTIVE_STATUS = "active"
ENDED_STATUS = "ended"

WEB_CHANNEL = "web"
PHONE_CHANNEL = "phone"
CHANNELS = (WEB_CHANNEL, PHONE_CHANNEL)
INBOUND_DIRECTION = "inbound"
OUTBOUND_DIRECTION = "outbound"
DIRECTIONS = (INBOUND_DIRECTION, OUTBOUND_DIRECTION)
USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
TRANSCRIPT_ROLES = (USER_ROLE, ASSISTANT_ROLE)

ANALYSIS_PENDING = "pending"
ANALYSIS_DONE = "done"
ANALYSIS_SKIPPED = "skipped"
ANALYSIS_FAILED = "failed"
SENTIMENTS = ("positive", "neutral", "negative")

# Voice-to-voice: from the caller stopping to the agent's first audio.
LATENCY_FIELD = "e2e_latency"
# How the dashboard names calls that ended without an outcome.
NO_OUTCOME = "none"
