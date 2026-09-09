# 🎬 That's a Wrap! — Submission Build

An AI-assisted filmmaking control room designed around a real execution pipeline:

**Script → Director Agent → Scenes → Footage → Editor + Specialist Agents → FFmpeg → QC → Human Approval → Final Film**

This repository is a self-contained contingency/submission build. It is intentionally local-first so the demo can run without a cloud deployment, while keeping Gemini, Google Cloud Storage, Cloud Run, ADK, and Grafana integration points ready.

## What is genuinely implemented

### Person 1 — AI / Intelligent Production
- Director Agent: screenplay → structured 10-scene breakdown
- Editor Agent: ranks uploaded takes and returns structured edit decisions
- Sound Agent
- Music Agent
- Colour Agent
- VFX Agent
- QC Agent: validates real media with ffprobe
- Production Agent: diagnoses failed jobs and chooses retry/escalation strategy
- Gemini structured-output integration when `GEMINI_API_KEY` is present
- Deterministic fallback mode when Gemini is unavailable
- Shared Pydantic contracts for scene/job/agent data

### Person 2 — Media / Processing
- Real video uploads
- FFmpeg transcode/edit pipeline
- H.264/AAC delivery output
- Audio extraction
- Audio normalization
- Audio replacement
- Audio mixing
- Scene concatenation / final-film assembly
- ffprobe-based QC
- OpenCV thumbnail tooling
- Persistent local media/state directories

### Platform / Demo Infrastructure
- React + TypeScript frontend connected to FastAPI
- Persistent JSON state so restarts don't erase the demo workspace
- Processing jobs and statuses
- Human review / approval
- Agent status endpoint
- Production activity feed
- Prometheus metrics endpoint
- Local Grafana + Prometheus stack
- Dockerfile and Cloud Run manifest

## Requirements

- Node.js 20+
- Python 3.11+
- FFmpeg + ffprobe on PATH
- Optional: Gemini API key
- Optional: Docker Desktop for Grafana

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/health  
API docs: http://localhost:8000/docs  
Metrics: http://localhost:8000/metrics

### 2. Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally http://localhost:5173.

### 3. Grafana

Keep the backend running, then in another terminal:

```bash
cd observability
docker compose up -d
```

Grafana: http://localhost:3000  
Prometheus: http://localhost:9090

The dashboard is provisioned automatically. Prometheus scrapes the backend's `/metrics` endpoint.

## Demo script

1. Open **Projects**.
2. Create a project and paste/import a screenplay as `.txt`.
3. The Director Agent creates 10 structured scenes.
4. Open **Scenes** and upload a real MP4/MOV/AVI/MKV/WebM/M4V clip.
5. Process the scene.
6. The Editor Agent ranks takes; Sound, Music, Colour and VFX agents generate plans.
7. FFmpeg creates the real processed output.
8. QC validates the output.
9. Open **Review Scenes** and play the real video.
10. Approve the scene.
11. Repeat for additional scenes.
12. Open the project and click **Assemble Final Film**.
13. Watch the assembled final output.
14. Open Grafana to show job counts, agent calls, failures and processing time.

## Gemini

Create `backend/.env` and set:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.7-flash
```

Without a key, Director and Editor use deterministic fallback logic so the media pipeline remains demoable.

## Architecture

```text
React / TypeScript
        ↓
     FastAPI
        ↓
  ┌───────────────┐
  │ Agent Layer   │
  │ Director      │
  │ Editor        │
  │ Sound         │
  │ Music         │
  │ Colour        │
  │ VFX           │
  │ QC            │
  │ Production    │
  └───────┬───────┘
          ↓
     Processing Job
          ↓
    FFmpeg / OpenCV
          ↓
       QC Result
          ↓
    Human Approval
          ↓
     Final Assembly
          ↓
       Film Output

Telemetry → OTLP → Grafana Cloud Tempo

Live UI telemetry → FastAPI `/observability/live` → Grafana Cloud/Tempo (server-side token) → sanitized React view

Local metrics → /metrics → Prometheus → Grafana
```

## Submission positioning

This build is designed to demonstrate the core product loop, not to claim Hollywood-grade autonomous filmmaking. The strongest demo story is that AI makes structured production decisions, deterministic media infrastructure executes those decisions, QC validates the output, a human approves the result, and the production control room exposes operational telemetry.

## Shared contract

The canonical names are defined in `backend/app/schemas/contracts.py`. Avoid changing `project_id`, `scene_id`, `job_id`, `status`, `input_files`, `output`, and the job/scene status values without coordinating across the team.


## Production Diagnostics + Grafana MCP

The app includes a **Production Diagnostics** page in the System navigation. It runs safe, secret-free checks for the API, FFmpeg, OpenCV, Gemini mode, OTLP configuration, and Grafana MCP configuration. It also shows recent failed post-production jobs and provides a safe **Retry / recover** action for failed jobs.

Grafana MCP remains a separate observability client: it queries telemetry stored in Grafana (Tempo/Loki/Mimir) through the MCP server. The Diagnostics page does not expose tokens or pretend to be the MCP server; it provides local failure context and ready-made MCP investigation prompts.

The VS Code MCP configuration is preserved at `.vscode/mcp.json` and targets Grafana's hosted MCP endpoint. The production ADK agent uses the official `grafana/mcp-grafana` server deployed on Cloud Run and connects to it over Streamable HTTP using the service-account credential supplied by deployment secrets. Grafana and OTLP credentials remain outside source control.


## Reliability update — persistent post-production jobs

The post-production job registry is persisted in `backend/media/state.json` and reloaded on backend startup. If a backend restart interrupts a `PENDING`, `PROCESSING`, or `RETRYING` job, the job is explicitly marked `FAILED` with a recovery message and its scene is moved out of `PROCESSING`. This prevents stale processing states and lets the Diagnostics Error Center retry the job safely.

The frontend also has a polling safety timeout and detects missing jobs instead of spinning forever. Recovery is scheduled as a background operation rather than blocking the Diagnostics page.

Uploading footage no longer falsely marks a scene as actively processing; the user must explicitly start AI post-production.


## Live Grafana telemetry in the app

The Agents page now polls `/observability/live` every five seconds. The backend queries Grafana Cloud's Tempo datasource server-side and returns sanitized recent traces. No Grafana credential is sent to the browser.

Set `GRAFANA_URL`, `GRAFANA_OBSERVABILITY_TOKEN`, and preferably `GRAFANA_TEMPO_DATASOURCE_UID` in `backend/.env`. For the website, use a dedicated read/query credential with only the permissions needed to read/query the Tempo datasource. Keep the existing Grafana MCP credential separate.

The browser only needs `VITE_API_URL` in `frontend/.env`.


## Observability rebuild (v3)

The contingency build now treats observability as a first-class subsystem.

### What changed

- `backend/app/config.py` loads the **same** `backend/.env` for Pydantic settings and runtime configuration. This fixes the previous bug where `.env` values were visible to `Settings()` but invisible to `os.getenv()`.
- OpenTelemetry now reads `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` from `settings`. If the endpoint is absent, the app does not create a fake localhost exporter.
- Structured application logs are exported through the same OTLP gateway as traces (`/v1/logs`), so Grafana/Loki can correlate detailed activity with traces without a custom Loki client.
- The Diagnostics page shows core runtime health, all registered agents, job failures, OTLP configuration, Grafana API health, MCP server health, and a detailed persistent event stream.
- Detailed diagnostic events are persisted in `backend/media/state.json` under `diagnostic_events`.
- Local Docker observability now includes Prometheus, Loki, Tempo and Grafana.
- Tempo MCP is enabled in the local Tempo configuration.
- `grafana-mcp/` documents and runs the official Grafana MCP server on port 8001 in read-only SSE mode.
- Grafana MCP credentials remain separate from the backend's read/query credential.

### The 401 fix

The original application had a configuration split:

1. `pydantic-settings` loaded `backend/.env` through `SettingsConfigDict(env_file=".env")`.
2. `main.py` then read OTLP and Grafana variables with `os.getenv()`.
3. `os.getenv()` was empty when the variables existed only in `.env`.
4. The OTLP exporter therefore sent no Grafana authorization header and Grafana returned `401 Unauthorized`.

The rebuilt version uses `settings.otel_exporter_otlp_endpoint` and `settings.otel_exporter_otlp_headers` directly. Grafana Cloud's documented direct OTLP configuration uses the OTLP gateway endpoint plus an `Authorization=Basic ...` header. Keep the exact values supplied by your Grafana Cloud stack in `backend/.env`.

### Verification

From `backend`:

```powershell
python -c "from app.config import settings; print(bool(settings.grafana_url), bool(settings.otel_exporter_otlp_endpoint), bool(settings.otel_exporter_otlp_headers))"
```

Then:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Open `/docs` and run:

- `GET /diagnostics`
- `POST /diagnostics/run`
- `GET /diagnostics/activity`

Run Grafana MCP separately:

```powershell
cd grafana-mcp
.
un-grafana-mcp.ps1
```

Then confirm:

`http://localhost:8001/healthz`

### Architecture

```text
That's a Wrap!
      |
      +--> FastAPI / agents / media / jobs
      |          |
      |          +--> structured diagnostic events
      |          +--> OpenTelemetry traces
      |          +--> Prometheus metrics
      |
      +--> Diagnostics UI
      |          |
      |          +--> local application state
      |          +--> Grafana / Tempo preview (server-side)
      |          +--> MCP health/configuration
      |
      +--> Grafana MCP
                 |
                 +--> Prometheus / PromQL
                 +--> Loki / LogQL
                 +--> Grafana dashboards
                 +--> alerting / incident workflows
                 +--> Tempo trace tools via Grafana's proxied MCP support
```

## Google Cloud runtime integration

That's a Wrap! uses Google Cloud at runtime in two ways:

- Gemini + Google ADK power the AI production workflow.
- Google Cloud Storage stores successfully processed scene renders and final-film assets when `GCS_BUCKET` is configured.

The backend uses Google Cloud Application Default Credentials (ADC), so no service-account private key is stored in the repository.

For local development, authenticate with:

```powershell
gcloud auth application-default login
```

Then set these non-secret settings in `backend/.env`:

```text
GOOGLE_CLOUD_PROJECT=your-google-cloud-project-id
GCS_BUCKET=your-unique-gcs-bucket-name
```

Verify without printing credentials:

```powershell
python backend\verify_google_cloud.py
```

A successful scene post-production uploads the rendered MP4 to `gs://<bucket>/scenes/...`, and final assembly uploads to `gs://<bucket>/projects/.../final/...`.
