# Voice Agent Studio: AI Phone Agents Without Code (LiveKit + LangChain)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

**Every business wants an AI on its phone line, but each agent still needs an engineer to build.**
Voice Agent Studio lets a business build its own voice agents in the browser: design the
conversation, test it, put it on a phone number, and see how every call went.

- **Front desk:** a caller asks for the skin doctor on Wednesday; the agent finds the doctor's free
  times in Cal.com, reads the details back and books the slot.
- **Reminder calls:** upload tomorrow's patients as a CSV and press start; each one ends confirmed,
  rescheduled, on voicemail or retried, and anyone who says stop is never called again.
- **A person when needed:** a caller who asks for a human is put through to the front desk.
- **After every call:** the transcript, summary, success, cost and reply speed land on the
  dashboard, and in HubSpot, Slack, Google Sheets or any webhook.

**The LLM can't skip a step:** code moves the call forward only once every detail is collected or
the booking has gone through.

---

## Architecture

<p align="center">
  <img src="docs/images/architecture.png" alt="A business team builds agents in the console, which saves them to the API and Postgres. Callers reach LiveKit Cloud by phone (SIP) or browser (WebRTC). The agent runtime gets the agent and its flow from the API, runs the flow step by step in one process per call, talks to the AI models (speech, LLM, voice) and uses live tools such as Cal.com or your own API. When a call ends, the worker analyses it and sends the result to your apps (HubSpot, Slack, Sheets); the worker also places campaign calls through LiveKit." width="85%">
</p>

- **Agents are data, not code:** one runtime serves every agent and loads its flow when a call starts.
- **Every call is a LiveKit room:** browser tests, incoming phone calls and campaign calls all run the same way.
- **The API is never in the audio path:** it is asked at the start, at the end, and for tools.
- **Slow work runs in a worker:** campaign dialling, post-call analysis, deliveries to other apps, document ingestion.
- **Keys never reach the LLM:** stored encrypted, filled in only when a tool sends a request.

## Concepts used

| Concept | In this project |
|---|---|
| **Real-time voice pipeline** | Streaming speech-to-text → LLM → voice over WebRTC and SIP, with turn detection and interruptions |
| **LLM wrapped in a state machine** | Code moves the call between steps; the LLM only talks inside one, with that step's prompt and tools |
| **Config-driven agent runtime** | Agents are configuration; one worker pool runs any agent, one process per call |
| **Tool calling with guardrails** | Each step can only use its own tools; bookings are idempotent and confirmed before they happen |
| **SIP telephony** | Inbound and outbound trunks, dispatch rules, answering-machine detection, transfer to a person |
| **Outbound campaign scheduler** | Calling windows per time zone, a concurrency limit, retries, consent and opt-outs, no double dials |
| **LLM-as-judge analytics** | Typed structured output per agent: summary, success, sentiment, custom fields, QA score |
| **Unit economics per call** | Token, speech and voice usage metered and priced for every call |
| **Hybrid RAG** | pgvector nearest neighbours re-ranked with keyword overlap |
| **Secure integrations** | Encrypted secrets, injection-safe templating, HMAC-signed webhooks retried with backoff |
| **Observability** | Langfuse traces per call, reply latency per turn, every tool call logged |
| **Provider-agnostic AI** | LLM, embeddings and speech chosen by a config string through LangChain |

## Demo videos

**[Build an agent from scratch](docs/demo/build-agent.mp4)** (2.5 min; the preview plays at 3.5×): a name, a greeting and
instructions, one step that collects name, phone and day, an ending, publish, and a test call.

<p align="center"><a href="docs/demo/build-agent.mp4"><img src="docs/demo/build-agent.gif" alt="The flow builder at the end of the build: a one-step callback flow ending in callback_requested, and the test call that collected name, phone and day" width="85%"></a></p>

**[A booking by voice](docs/demo/voice-demo.mp4)** (1.5 min with sound; the preview plays silent at 2.5×): the caller speaks, the
agent checks the doctor's free times, reads the details back and books.

<p align="center"><a href="docs/demo/voice-demo.mp4"><img src="docs/demo/voice-demo.gif" alt="A voice test call in the clinic flow: the caller's spoken lines as text, the read-back, and the booking ID" width="85%"></a></p>

**[A reminder campaign](docs/demo/campaign.mp4)** (1 min; the preview plays at 1.5×): upload a CSV and start; six real phone
calls end confirmed, moved, opted out, on voicemail, not reached, or never called.

<p align="center"><a href="docs/demo/campaign.mp4"><img src="docs/demo/campaign.gif" alt="A finished reminder campaign: six contacts with their outcomes" width="85%"></a></p>

## Screenshots

**A Cal.com tool in the flow builder:** each doctor is a Cal.com event type.

<p align="center"><img src="docs/images/flow-calcom.png" alt="The clinic flow in the flow builder with the check_availability tool selected: kind 'Cal.com: free times', the CALCOM_KEY secret, time zone, and four doctors each with a Cal.com event type ID and the words callers use" width="85%"></p>

**A call:** the analysis, transcript, tool calls, cost, and what was sent after the call.

<p align="center"><img src="docs/images/call-detail.png" alt="A call's page: post-call analysis (successful, sentiment positive, QA 5/5), the transcript of a Cal.com booking, the tool calls with their results and times, cost, collected fields, and two signed webhooks sent after the call" width="85%"></p>

**The dashboard:** outcomes, cost, reply speed and success by agent.

<p align="center"><img src="docs/images/overview.png" alt="The overview dashboard: calls, average cost, average length, reply delay typical and slow, calls per day, outcomes, and success by agent" width="85%"></p>

## Results from real runs

| Measure | Result |
|---|---|
| **Reply time** on voice calls (caller stops → agent starts speaking) | 2.25 s typical (p50), 4.23 s slow (p95) |
| Where that time goes | speech-to-text ~0.45 s, voice starts in 0.3-0.5 s, the rest is the LLM |
| **Cost per call** (LLM, speech, voice and post-call analysis) | $0.005 on average over 93 calls; $0.006 for a full typed booking |
| **Post-call analysis accuracy** on 11 real calls with known answers | 33 / 33 answers right, 1.2-2.8 s per call |
| **Calendar booking** with Cal.com during a call | free times in ~0.5 s, booking in ~2.4 s (the agent says "One moment" meanwhile) |
| **Campaigns** | every contact ends with an outcome; calls at once stay within the set limit |

## Run it locally

You need Docker, a [LiveKit Cloud](https://cloud.livekit.io) project (free plan), an OpenAI API key
and a Deepgram key.

```powershell
Copy-Item .env.example .env.local      # LIVEKIT_*, OPENAI_API_KEY, DEEPGRAM_API_KEY, RUNTIME_API_TOKEN, SECRETS_KEY
docker compose up -d --build
```

- Console: <http://localhost:3000> (Overview shows every service's health)
- API docs: <http://localhost:8000/docs>

Then: **Agents → Clinic booking → Open flow builder → Start test call**, and book an appointment,
or pick **Start from scratch** to build your own. For a phone number, add one under **Phone
numbers**; for Cal.com, save your key under **Integrations** and create an agent from **Clinic
booking (Cal.com)**.

**Commands**

| What | Command |
|---|---|
| API tests | `cd api; .\.venv\Scripts\python.exe -m pytest` |
| Runtime tests | `cd runtime; .\.venv\Scripts\python.exe -m pytest` |
| Lint and format check (Python) | `.\.venv\Scripts\ruff.exe check . ; .\.venv\Scripts\ruff.exe format --check .` |
| Console | `cd console; npm run dev` · `npm run lint` · `npm run build` |

Each Python app has its own virtual environment:
`python -m venv .venv` then `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`.

## Project structure

```text
voice-agent-studio/
├── api/                       control plane (FastAPI)
│   ├── src/studio_api/
│   │   ├── agents/            agents, templates, browser-call tokens, runtime config
│   │   ├── flows/             flow schema, validation, draft/publish, flow templates
│   │   ├── knowledge/         knowledge bases, ingestion, hybrid search
│   │   ├── numbers/           phone numbers, SIP trunks, outbound calls
│   │   ├── campaigns/         campaigns, contacts, CSV import, the dialler
│   │   ├── calls/             call records, cost, post-call analysis, dashboard
│   │   ├── secrets/           encrypted keys and tokens
│   │   ├── after_call/        webhooks, Slack, HubSpot, Google Sheets, deliveries
│   │   ├── demo_clinic/       a stand-in hospital booking API for the clinic template
│   │   └── main.py · worker.py · storage.py · jobs.py · health.py · tracing.py
│   ├── migrations/            Alembic (0001-0011)
│   └── tests/
├── runtime/                   agent runtime (LiveKit Agents)
│   ├── src/studio_runtime/
│   │   ├── flows/             flow runner, per-step graph, HTTP and Cal.com tools, prompts
│   │   ├── parsers/           reading typed answers, per language
│   │   └── worker.py · phone.py · control_plane.py · channels.py · providers.py · observability.py
│   └── tests/
├── console/                   Next.js console (and its read-only demo build)
├── site/                      the product page (static)
├── tools/                     scenarios, campaign and Cal.com live checks, analysis eval, showcase, demo recorders
├── docs/                      architecture diagram, screenshots, demo videos
└── compose.yaml               Postgres (pgvector), Redis, RustFS, API, worker, runtime, console
```
