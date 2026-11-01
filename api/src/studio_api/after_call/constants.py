WEBHOOK_ACTION = "webhook"
SLACK_ACTION = "slack"
HUBSPOT_ACTION = "hubspot"
GOOGLE_SHEETS_ACTION = "google_sheets"
ACTION_KINDS = (WEBHOOK_ACTION, SLACK_ACTION, HUBSPOT_ACTION, GOOGLE_SHEETS_ACTION)
# Actions that send with a stored secret (the Slack webhook URL, a token, a service account).
ACTIONS_NEEDING_A_SECRET = (SLACK_ACTION, HUBSPOT_ACTION, GOOGLE_SHEETS_ACTION)

# call.ended: as soon as the runtime reports the call; call.analysed: once the post-call
# analysis is done (or was skipped), so the summary and success are in the payload.
CALL_ENDED = "call.ended"
CALL_ANALYSED = "call.analysed"
EVENTS = (CALL_ENDED, CALL_ANALYSED)

PENDING_DELIVERY = "pending"
SENT_DELIVERY = "sent"
FAILED_DELIVERY = "failed"
SKIPPED_DELIVERY = "skipped"

DELIVER_JOB = "deliver_job"
# Signed like Stripe's webhooks: HMAC-SHA256 of "<timestamp>.<body>" with the action's secret.
SIGNATURE_HEADER = "X-Studio-Signature"
TIMESTAMP_HEADER = "X-Studio-Timestamp"
EVENT_HEADER = "X-Studio-Event"
# The same on every retry of one delivery, so a receiver can drop duplicates.
DELIVERY_HEADER = "X-Studio-Delivery"
# 408 and 429 are worth retrying; other 4xx answers will not change.
RETRYABLE_STATUSES = (408, 429)
SERVER_ERROR_STATUS = 500
MAX_ERROR_CHARS = 500

HUBSPOT_API_URL = "https://api.hubapi.com"
# HubSpot's own association type for "note to contact".
HUBSPOT_NOTE_TO_CONTACT = 202
# Collected fields that name the person called, in order of preference.
NAME_FIELDS = ("patient_name", "customer_name", "name")
PHONE_FIELDS = ("phone", "caller_number")
EMAIL_FIELD = "email"

GOOGLE_SHEETS_API_URL = "https://sheets.googleapis.com/v4/spreadsheets"
GOOGLE_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GOOGLE_TOKEN_SECONDS = 3600
SHEET_COLUMNS = (
    "Ended (UTC)",
    "Agent",
    "Channel",
    "Direction",
    "Number",
    "Outcome",
    "Successful",
    "Summary",
    "Seconds",
    "Cost (USD)",
    "Call",
)
