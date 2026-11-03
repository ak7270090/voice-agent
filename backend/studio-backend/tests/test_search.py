from studio_backend.database import create_session_factory
from studio_backend.knowledge.ingestion import ingest_document
from studio_backend.knowledge.search import Candidate, content_words, rerank
from tests.conftest import WordEmbeddings
from tests.test_agents import create_agent
from tests.test_knowledge import create_knowledge_base, upload

DOCTORS = b"""# Doctors

Dr. Anjali Mehta is the dermatologist. She sees patients on Monday, Wednesday and Saturday.

Dr. Rao is the general physician. He sees patients every weekday morning.
"""
TIMINGS = b"""# Timings and location

The hospital is open from 8 am to 8 pm.

The address is 12 MG Road, Bengaluru.
"""


def test_question_words_ignore_filler_words():
    assert content_words("What is the address of the hospital?") == {"address", "hospital"}


def test_keyword_overlap_lifts_the_chunk_that_contains_the_asked_word():
    candidates = [
        Candidate("d1", "timings.md", "The hospital is open from 8 am to 8 pm.", 0.80),
        Candidate("d1", "timings.md", "The address is 12 MG Road.", 0.78),
    ]

    hits = rerank("What is the address?", candidates, keyword_weight=0.1, top_k=1)

    assert hits[0].text == "The address is 12 MG Road."
    assert hits[0].keyword_overlap == 1.0


async def ingest_all(postgres_engine, file_store, settings, knowledge_base_id, client):
    session_factory = create_session_factory(postgres_engine)
    for name, data in (("doctors.md", DOCTORS), ("timings.md", TIMINGS)):
        document = (await upload(client, knowledge_base_id, name=name, data=data)).json()
        await ingest_document(
            session_factory, file_store, WordEmbeddings(), settings, document["id"]
        )


async def test_search_finds_the_chunk_that_answers_the_question(
    postgres_client, postgres_engine, file_store, settings
):
    knowledge_base = await create_knowledge_base(postgres_client)
    await ingest_all(postgres_engine, file_store, settings, knowledge_base["id"], postgres_client)

    response = await postgres_client.post(
        f"/knowledge-bases/{knowledge_base['id']}/search",
        json={"query": "Which days does the dermatologist see patients?", "top_k": 2},
    )

    hits = response.json()
    assert response.status_code == 200
    assert len(hits) == 2
    assert "dermatologist" in hits[0]["text"]
    assert hits[0]["document_name"] == "doctors.md"


async def test_runtime_searches_only_the_agents_knowledge_bases(
    postgres_client, postgres_engine, file_store, settings, runtime_headers
):
    linked = await create_knowledge_base(postgres_client, "Linked")
    other = await create_knowledge_base(postgres_client, "Other")
    await ingest_all(postgres_engine, file_store, settings, other["id"], postgres_client)
    agent = await create_agent(postgres_client)
    path = f"/runtime/agents/{agent['id']}/knowledge-search"
    query = {"query": "What is the address?"}

    before = await postgres_client.post(path, json=query, headers=runtime_headers)
    await postgres_client.patch(
        f"/agents/{agent['id']}", json={"knowledge_base_ids": [linked["id"], other["id"]]}
    )
    after = await postgres_client.post(path, json=query, headers=runtime_headers)
    missing = await postgres_client.post(
        "/runtime/agents/missing/knowledge-search", json=query, headers=runtime_headers
    )

    assert before.json() == []
    assert "12 MG Road" in after.json()[0]["text"]
    assert missing.status_code == 404
