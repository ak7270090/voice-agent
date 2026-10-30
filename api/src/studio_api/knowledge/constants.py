# Size of the default embedding model (openai:text-embedding-3-small).
EMBEDDING_DIMENSIONS = 1536

QUEUED_STATUS = "queued"
PROCESSING_STATUS = "processing"
READY_STATUS = "ready"
FAILED_STATUS = "failed"

UPLOAD_SOURCE = "upload"
URL_SOURCE = "url"

INGEST_JOB_NAME = "ingest_document_job"
DOCUMENT_KEY_PREFIX = "documents"

# File types MarkItDown converts to Markdown.
SUPPORTED_EXTENSIONS = (
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",
    ".htm",
    ".md",
    ".txt",
    ".csv",
)

# Common words that say nothing about which chunk answers a question.
STOP_WORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "of",
        "for",
        "to",
        "in",
        "on",
        "at",
        "and",
        "or",
        "do",
        "does",
        "did",
        "what",
        "when",
        "where",
        "how",
        "which",
        "who",
        "can",
        "could",
        "i",
        "my",
        "me",
        "you",
        "your",
        "be",
        "it",
        "this",
        "that",
        "with",
        "from",
        "about",
        "there",
        "have",
        "has",
    ]
)
