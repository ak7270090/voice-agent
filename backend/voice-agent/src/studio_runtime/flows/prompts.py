"""How the current step is described to the LLM. These are instructions for the model, not words
for the caller (those come from the flow itself and locales/)."""

STEP_SECTION = """Today is {today}.

Current step: {step_name}
{step_instructions}"""

FIELDS_SECTION = """Details this step collects (ask for one missing detail at a time):
{lines}
Call save_fields as soon as the caller gives any of them, using their exact words, and write
your reply to the caller in the same message."""

FIELD_HAVE = "- {name} ({description}): have {value}"
FIELD_MISSING = "- {name} ({description}): still needed"

RESULTS_SECTION = """Latest result of {tool}:
{result}"""

MOVES_SECTION = """When one of these is true, call its tool
(never mention steps or tools to the caller):
{lines}"""

MOVE_LINE = "- {tool}: {condition}"

SAVE_FIELDS_DESCRIPTION = "Save details the caller gave. Pass only the ones they just said."
SAVED = "Saved."
STILL_NEEDED = "Still needed: {names}."
ALL_COLLECTED = "All details collected."
COULD_NOT_READ = "Could not read {name} from {value!r}; ask again."
MOVED = "Moved on to: {target}. Continue from there."
UNKNOWN_TOOL = "{name} is not available in this step."
AFTER_FAILURE = (
    "{tool} just failed (see its result above), so the call came back to this step. Tell the "
    "caller what happened in plain words and ask what they would like instead."
)
BACK_TO_CHANGE = (
    "The caller came back to this step to change something. Ask what they would like to "
    "change. When they say the new value, call save_fields with it: the details above keep the "
    "old value until you do."
)
TOOL_UNAVAILABLE = (
    "{name} got no answer: the service is unavailable. The caller has already been told it "
    "can't be checked right now. Offer to try again in a moment or to connect them to a person. "
    "Never guess the answer."
)
