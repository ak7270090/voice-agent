from studio_backend.core.database import create_session_factory
from studio_backend.knowledge.ingestion import ingest_document, split_into_chunks, to_markdown
from tests.conftest import WordEmbeddings
from tests.test_agents import create_agent

HOSPITAL_NOTES = b"""# Visiting hours

Visitors are welcome from 4 pm to 7 pm every day.

# Parking

Parking is free for patients in the basement.
"""


async def create_knowledge_base(client, name: str = "City Hospital") -> dict:
    response = await client.post("/knowledge-bases", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def upload(client, knowledge_base_id: str, name: str = "notes.md", data=HOSPITAL_NOTES):
    return await client.post(
        f"/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": (name, data, "text/markdown")},
    )


async def test_uploaded_file_is_stored_and_queued_for_ingestion(client, file_store, job_queue):
    knowledge_base = await create_knowledge_base(client)

    response = await upload(client, knowledge_base["id"])

    document = response.json()
    assert response.status_code == 202
    assert document["status"] == "queued"
    assert document["size_bytes"] == len(HOSPITAL_NOTES)
    assert list(file_store.files.values()) == [HOSPITAL_NOTES]
    assert job_queue.jobs == [("ingest_document_job", document["id"])]


async def test_unsupported_and_oversized_files_are_refused(client, settings, monkeypatch):
    knowledge_base = await create_knowledge_base(client)
    monkeypatch.setattr(settings, "max_upload_bytes", 10)

    assert (await upload(client, knowledge_base["id"], name="song.mp3")).status_code == 415
    assert (await upload(client, knowledge_base["id"])).status_code == 413


async def test_upload_to_a_missing_knowledge_base_is_not_found(client):
    assert (await upload(client, "missing")).status_code == 404


async def test_url_document_is_queued(client, job_queue):
    knowledge_base = await create_knowledge_base(client)

    response = await client.post(
        f"/knowledge-bases/{knowledge_base['id']}/documents/from-url",
        json={"url": "https://example.com/faq"},
    )

    assert response.status_code == 202
    assert response.json()["source_url"] == "https://example.com/faq"
    assert len(job_queue.jobs) == 1


async def test_deleting_a_document_or_knowledge_base_removes_stored_files(client, file_store):
    knowledge_base = await create_knowledge_base(client)
    first = (await upload(client, knowledge_base["id"], name="a.md")).json()
    await upload(client, knowledge_base["id"], name="b.md")
    path = f"/knowledge-bases/{knowledge_base['id']}"

    assert (await client.delete(f"{path}/documents/{first['id']}")).status_code == 204
    assert len(file_store.files) == 1
    assert (await client.delete(f"{path}/documents/{first['id']}")).status_code == 404
    assert (await client.delete(path)).status_code == 204
    assert file_store.files == {}
    assert (await client.delete(path)).status_code == 404


async def test_ingestion_chunks_and_embeds_the_document(
    client, sqlite_engine, file_store, settings
):
    knowledge_base = await create_knowledge_base(client)
    document = (await upload(client, knowledge_base["id"])).json()

    await ingest_document(
        create_session_factory(sqlite_engine),
        file_store,
        WordEmbeddings(),
        settings,
        document["id"],
    )

    documents = (await client.get(f"/knowledge-bases/{knowledge_base['id']}/documents")).json()
    listed = (await client.get("/knowledge-bases")).json()
    assert documents[0]["status"] == "ready"
    assert documents[0]["chunk_count"] >= 1
    assert listed[0]["document_count"] == 1
    assert listed[0]["chunk_count"] == documents[0]["chunk_count"]


async def test_document_without_text_is_marked_failed_with_the_reason(
    client, sqlite_engine, file_store, settings
):
    knowledge_base = await create_knowledge_base(client)
    document = (await upload(client, knowledge_base["id"], name="empty.txt", data=b"  ")).json()

    await ingest_document(
        create_session_factory(sqlite_engine),
        file_store,
        WordEmbeddings(),
        settings,
        document["id"],
    )

    failed = (await client.get(f"/knowledge-bases/{knowledge_base['id']}/documents")).json()[0]
    assert failed["status"] == "failed"
    assert "no text found" in failed["error"]


def test_markdown_splits_into_chunks_no_longer_than_the_setting(settings):
    text = to_markdown(HOSPITAL_NOTES * 20, "notes.md")

    chunks = split_into_chunks(text, settings)

    assert len(chunks) > 1
    assert all(len(chunk) <= settings.chunk_size_chars for chunk in chunks)


def test_html_is_read_as_markdown():
    markdown = to_markdown(
        b"<html><body><h1>Fees</h1><p>OPD fee is 500.</p></body></html>", "fees.html"
    )

    assert "# Fees" in markdown
    assert "OPD fee is 500." in markdown


async def test_agent_is_linked_to_knowledge_bases_and_the_runtime_sees_them(
    client, runtime_headers
):
    agent = await create_agent(client)
    knowledge_base = await create_knowledge_base(client)

    linked = await client.patch(
        f"/agents/{agent['id']}", json={"knowledge_base_ids": [knowledge_base["id"]]}
    )
    unknown = await client.patch(f"/agents/{agent['id']}", json={"knowledge_base_ids": ["nope"]})
    config = (await client.get(f"/runtime/agents/{agent['id']}", headers=runtime_headers)).json()

    assert linked.json()["knowledge_base_ids"] == [knowledge_base["id"]]
    assert unknown.status_code == 422
    assert config["knowledge_base_ids"] == [knowledge_base["id"]]
