DRAFT = "draft"
RUNNING = "running"
PAUSED = "paused"
COMPLETED = "completed"

# A contact's way through a campaign: pending → calling → done, or back to retry when nobody
# was reached, until the attempts run out (failed).
PENDING = "pending"
CALLING = "calling"
RETRY = "retry"
DONE = "done"
FAILED = "failed"
# Never dialled: no consent, or the person asked not to be called again.
SKIPPED = "skipped"
OPTED_OUT = "opted_out"
CONTACT_STATUSES = (PENDING, CALLING, RETRY, DONE, FAILED, SKIPPED, OPTED_OUT)
WAITING = (PENDING, RETRY)
OPEN = (PENDING, RETRY, CALLING)

# Call outcomes (from the runtime or an End node) that decide what happens to a contact.
NOBODY_REACHED_OUTCOMES = ("not_answered", "answering_machine")
OPT_OUT_OUTCOME = "opted_out"

MAX_CONCURRENT_CALLS = 5
MAX_ATTEMPTS = 5
CSV_PHONE_COLUMN = "phone"
CSV_NAME_COLUMN = "name"
CSV_CONSENT_COLUMN = "consent"
CONSENT_YES = ("yes", "y", "true", "1")
