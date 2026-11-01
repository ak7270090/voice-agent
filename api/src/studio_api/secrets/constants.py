# Secret names as tools use them: {secret.CALCOM_KEY}.
SECRET_NAME_PATTERN = r"^[A-Z][A-Z0-9_]*$"
SECRET_NAME_MAX_LENGTH = 60
SECRET_VALUE_MAX_LENGTH = 10_000
# How much of a value the console shows: the first and last few characters of a long one.
PREVIEW_EDGE_CHARS = 4
PREVIEW_MIN_LENGTH = 12
HIDDEN_PREVIEW = "••••"
