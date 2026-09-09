# 🎬 That's a Wrap!

> **AI-assisted filmmaking and post-production with real-time observability.**

**That's a Wrap!** is an AI-assisted filmmaking and post-production platform that turns raw footage into production-ready scenes while giving filmmakers and developers a transparent view of what is actually happening behind the scenes.

Instead of hiding the production pipeline behind a single **"Generate"** button, That's a Wrap! exposes the workflow:

```text
Footage
   ↓
AI Orchestration
   ↓
Editing / Production
   ↓
FFmpeg Rendering
   ↓
Quality Control
   ↓
Google Cloud Storage
   ↓
Real-Time Observability
```

The platform combines:

- Google Gemini
- Google ADK
- Grafana MCP
- Grafana Cloud
- OpenTelemetry
- Grafana Tempo
- Grafana Loki
- Prometheus
- Grafana Alerting
- FFmpeg
- OpenCV
- Google Cloud Storage
- Google Cloud Run
- React
- TypeScript
- FastAPI

into one end-to-end filmmaking workflow.

---

# ✨ Why That's a Wrap?

Modern AI video tools can make the creative process feel magical — but that magic often comes at the cost of transparency.

That's a Wrap! takes a different approach.

The platform is designed around a simple principle:

> **If the system says something happened, there should be real runtime evidence behind it.**

That means the application does **not** intentionally invent:

- fake AI activity
- fake processing progress
- fake cloud health
- fake trace counts
- fake logs
- fake MCP calls
- fake rendering results

When information is unavailable, the system should say so.

When an operation happens, the system can expose evidence from the actual runtime.

---

# 🚀 Core Features

## 🎥 AI-Assisted Post-Production

That's a Wrap! uses AI agents to assist with filmmaking and post-production decisions.

The project includes agents for areas such as:

- Direction
- Editing
- Production
- Quality control
- Specialist tasks

The goal is not to replace deterministic media tooling with an AI model.

Instead, AI helps reason about the production context while the actual media pipeline remains deterministic and testable.

---

# 🤖 Gemini + Google ADK Orchestration

Google Gemini and the Google Agent Development Kit are used for autonomous orchestration.

The production orchestrator can:

```text
Receive scene/job context
        ↓
Invoke Gemini / ADK
        ↓
Access Grafana MCP
        ↓
Inspect real observability data
        ↓
Return an evidence-based response
        ↓
Continue deterministic media processing
```

The architecture deliberately separates:

```text
AI Reasoning
     │
     │
     ▼
Gemini + Google ADK
```

from:

```text
Deterministic Production
     │
     ├── FFmpeg
     ├── OpenCV
     ├── QC
     └── GCS
```

This means a slow AI call does not unnecessarily prevent the actual media pipeline from progressing.

---

# 🔌 Real Grafana MCP Integration

Grafana MCP is a real runtime dependency — not a decorative integration.

The backend connects to a deployed Grafana MCP server using **Streamable HTTP**.

The MCP server exposes Grafana capabilities to both:

```text
That's a Wrap Backend
```

and:

```text
Gemini / Google ADK
```

The runtime has successfully exercised real MCP tools including:

```text
list_datasources
query_loki_logs
tempo_traceql-search
alerting_manage_rules
list_loki_label_names
list_loki_label_values
query_prometheus
list_prometheus_metric_names
```

The application's Diagnostics page exposes the MCP connection and actual tool activity returned by the server.

---

# 🧠 AI + MCP Architecture

```text
                         ┌─────────────────────────┐
                         │       Web Frontend       │
                         │      React + Vite        │
                         └────────────┬────────────┘
                                      │
                                      │ HTTP
                                      ▼
                         ┌─────────────────────────┐
                         │      FastAPI Backend     │
                         │      That's a Wrap API   │
                         └────────────┬────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
          ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
          │ Gemini + ADK   │  │ Media Workflow │  │ Google Cloud   │
          │                │  │                │  │ Storage        │
          │ AI reasoning   │  │ Deterministic  │  │                │
          │ orchestration  │  │ production     │  │ Rendered media │
          └───────┬────────┘  └───────┬────────┘  └────────────────┘
                  │                   │
                  │                   │
                  ▼                   ▼
          ┌────────────────┐  ┌────────────────┐
          │   Grafana MCP  │  │     FFmpeg     │
          │                │  │    + OpenCV    │
          │ Runtime access │  │      + QC       │
          │ to Grafana     │  │                │
          └───────┬────────┘  └────────────────┘
                  │
                  ▼
        ┌─────────────────────────────┐
        │       Grafana Cloud         │
        │                             │
        │  Loki    Tempo    Prometheus│
        │                             │
        │       Grafana Alerting      │
        └─────────────────────────────┘
```

---

# 🔄 End-to-End Production Workflow

A typical scene processing flow looks like this:

```text
┌───────────────────────┐
│    Upload Footage     │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Create / Select       │
│ Project               │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Create Scene          │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────────────────────────┐
│          Start Production Job             │
└───────────────────────┬───────────────────┘
                        │
             ┌──────────┴───────────┐
             │                      │
             ▼                      ▼
┌──────────────────────┐  ┌──────────────────────┐
│ Gemini / ADK         │  │ Deterministic Media  │
│ Orchestration        │  │ Worker               │
│                      │  │                      │
│ • Reasoning          │  │ • FFmpeg             │
│ • MCP                │  │ • Audio              │
│ • Grafana inspection │  │ • Video              │
└──────────┬───────────┘  └──────────┬───────────┘
           │                         │
           ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│ Grafana MCP          │  │ Rendered Media       │
│                      │  │                      │
│ • Loki               │  │ MP4                  │
│ • Tempo              │  └──────────┬───────────┘
│ • Alerting            │             │
└──────────────────────┘             ▼
                            ┌──────────────────────┐
                            │ Quality Control      │
                            │                      │
                            │ • Duration           │
                            │ • Audio              │
                            │ • Video              │
                            │ • Validation         │
                            └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │ Google Cloud Storage │
                            └──────────────────────┘
```

The AI orchestration and media pipeline run independently so that observability analysis does not unnecessarily delay rendering.

---

# 📊 Grafana Cloud Observability

The backend emits OpenTelemetry telemetry to Grafana Cloud.

The observability stack uses:

| Component | Purpose |
|---|---|
| Grafana Tempo | Distributed traces |
| Grafana Loki | Application logs |
| Prometheus | Metrics |
| Grafana Alerting | Alert state |
| Grafana MCP | Runtime access to Grafana |

The backend service is identified as:

```text
thats-a-wrap-backend
```

Real traces have been observed for endpoints including:

```text
GET /diagnostics/mcp
GET /observability/links
GET /agents/status
GET /diagnostics/activity
GET /diagnostics
```

---

# 🔭 OpenTelemetry → Grafana Cloud

The telemetry path looks like this:

```text
┌──────────────────────────┐
│      FastAPI Backend     │
│                          │
│ thats-a-wrap-backend     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│    OpenTelemetry SDK     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│    Grafana Cloud OTLP    │
└────────────┬─────────────┘
             │
       ┌─────┼─────┐
       │     │     │
       ▼     ▼     ▼
     Tempo  Loki  Metrics
```

This makes application activity searchable in Grafana Cloud.

---

# 🔎 Runtime Evidence Control Room

The Diagnostics page is designed as an observability control room rather than a static status page.

It can display:

- MCP connection state
- MCP tool count
- Grafana datasource information
- Loki log results
- Tempo trace results
- Grafana alert rules
- exact LogQL queries
- exact TraceQL queries
- MCP tool arguments
- MCP tool success/failure
- ADK execution state
- Gemini/ADK function-call counts
- MCP invocation evidence
- live production activity
- job and scene events
- failure information

The objective is to make the system **inspectable**.

---

# 🛰️ MCP Runtime Architecture

There are two separate credential paths.

## MCP Server → Grafana Cloud

The deployed Grafana MCP server uses its Grafana service-account credential to communicate with Grafana Cloud.

## Application → MCP Server

The That's a Wrap! backend authenticates to the MCP server using the MCP server caller token.

Conceptually:

```text
┌──────────────────────────────┐
│   That's a Wrap Backend      │
└──────────────┬───────────────┘
               │
               │ Bearer authentication
               ▼
┌──────────────────────────────┐
│   Grafana MCP on Cloud Run   │
└──────────────┬───────────────┘
               │
               │ Grafana service account
               ▼
┌──────────────────────────────┐
│       Grafana Cloud          │
│                              │
│ Loki / Tempo / Prometheus    │
│ Alerting / Datasources       │
└──────────────────────────────┘
```

Keeping these credentials separate makes the integration easier to reason about and secure.

---

# 🔌 MCP Runtime Evidence

The project includes runtime verification utilities.

For example:

```bash
python backend/verify_grafana_mcp.py
```

The MCP diagnostics endpoint is:

```text
GET /diagnostics/mcp
```

The live MCP observability endpoint is:

```text
GET /observability/mcp
```

The endpoint can return:

```text
MCP connection
Tool count
Grafana datasources
Loki logs
Tempo traces
Alert state
MCP tool activity
Queries
Errors
Timestamps
```

This gives the application a concrete runtime path for proving MCP participation.

---

# 🤖 ADK Runtime Evidence

The production orchestrator records information about ADK execution.

The Diagnostics UI can expose:

```text
Executed
Degraded
MCP invoked
Function calls
Function responses
Job
Scene
MCP tools
Tool arguments
Final response
Errors
```

The ADK agent is intentionally instructed to avoid fabricating telemetry.

When matching Grafana data does not exist, the expected behavior is to report that no matching telemetry was returned rather than inventing a result.

---

# 📡 Example Grafana Queries

## Loki

The application can query application logs using LogQL:

```logql
{service_name="thats-a-wrap-backend"}
```

For post-production activity:

```logql
{service_name="thats-a-wrap-backend"} |= "post-production"
```

These logs can be inspected directly in Grafana Explore.

---

## Tempo

The application can query traces using TraceQL:

```traceql
{ resource.service.name = "thats-a-wrap-backend" }
```

For job/scene-specific investigation, the query can be narrowed using job or scene attributes when those attributes are available.

---

# 🎞️ Real Media Processing

That's a Wrap! uses **FFmpeg** for actual media rendering.

The renderer supports:

- video processing
- audio mixing
- background music
- audio normalization
- audio resampling
- trimming
- padding
- timestamp correction
- MP4 generation

The current performance-oriented FFmpeg configuration uses:

```text
Preset: superfast
CRF: 21
Threads: automatic
```

The goal is to keep demo rendering responsive while maintaining useful visual quality.

---

# 🧪 Quality Control

Rendered scenes are not simply assumed to be valid.

The workflow performs media checks including:

- video duration
- audio duration
- duration mismatch
- output validation
- render success/failure

During development, the QC pipeline caught a real mismatch:

```text
Video duration: 41.4 seconds
Audio duration: 39.6 seconds
Difference:     1.8 seconds
```

The renderer was subsequently updated to handle audio synchronization using FFmpeg filters including:

```text
aresample=48000:async=1:first_pts=0
apad
atrim
asetpts
```

Music tracks are similarly padded/trimmed and the final mixed audio is normalized to the expected duration.

This is an important design principle:

> **A successful FFmpeg process does not automatically mean that the final scene is valid.**

---

# ☁️ Google Cloud Storage

Rendered assets can be uploaded to Google Cloud Storage.

The backend uses Google Cloud authentication through Application Default Credentials.

The workflow can therefore move from:

```text
Local Media
     │
     ▼
FFmpeg Render
     │
     ▼
Quality Control
     │
     ▼
Google Cloud Storage
```

For demonstrations, actual bucket objects can be inspected directly rather than relying on a generic Google Cloud landing page.

---

# 🖥️ Frontend

The frontend is built with:

- React
- TypeScript
- Vite

Major screens include:

```text
Projects
Open Project
New Project
Scenes
New Scene
Upload Footage
Review Scenes
Activity
Agents
Diagnostics
Settings
Profile
```

The **Diagnostics** screen acts as the technical control room for the application.

---

# 🗂️ Project Structure

```text
That's-A-Wrap/
│
├── backend/
│   │
│   ├── adk_app/
│   │   ├── __init__.py
│   │   └── agent.py
│   │
│   ├── app/
│   │   ├── agents/
│   │   │   ├── director.py
│   │   │   ├── editor.py
│   │   │   ├── gemini_client.py
│   │   │   ├── production.py
│   │   │   ├── qc.py
│   │   │   └── specialists.py
│   │   │
│   │   ├── media/
│   │   │   ├── ffmpeg_engine.py
│   │   │   └── opencv_tools.py
│   │   │
│   │   ├── schemas/
│   │   │   └── contracts.py
│   │   │
│   │   ├── services/
│   │   │   ├── adk_orchestrator.py
│   │   │   └── workflow.py
│   │   │
│   │   ├── storage/
│   │   │   └── gcs.py
│   │   │
│   │   ├── config.py
│   │   ├── grafana_live.py
│   │   ├── main.py
│   │   ├── mcp_grafana.py
│   │   ├── mcp_observability.py
│   │   ├── observability.py
│   │   └── store.py
│   │
│   ├── tests/
│   │   └── test_contracts.py
│   │
│   ├── Dockerfile
│   ├── cloudrun.yaml
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── test_mcp_runtime.py
│   ├── verify_google_cloud.py
│   └── verify_grafana_mcp.py
│
├── frontend/
│   │
│   ├── public/
│   │
│   └── src/
│       ├── pages/
│       │   ├── Activity.tsx
│       │   ├── Agents.tsx
│       │   ├── Diagnostics.tsx
│       │   ├── NewProject.tsx
│       │   ├── NewScene.tsx
│       │   ├── OpenProject.tsx
│       │   ├── Profile.tsx
│       │   ├── Projects.tsx
│       │   ├── ReviewScenes.tsx
│       │   ├── Scenes.tsx
│       │   ├── Settings.tsx
│       │   └── UploadFootage.tsx
│       │
│       ├── App.tsx
│       ├── App.css
│       ├── api.ts
│       └── index.css
│
├── grafana-mcp/
│   ├── README.md
│   └── .env.example
│
├── observability/
│   ├── grafana/
│   │   ├── dashboard.json
│   │   └── provisioning/
│   │       ├── dashboards/
│   │       └── datasources/
│   │
│   ├── loki-config.yml
│   ├── prometheus.yml
│   ├── tempo-config.yml
│   └── docker-compose.yml
│
├── CLOUD_MCP_RUNTIME_UPDATE.md
├── CONTRACTS.md
├── FINAL_DEMO_RUNTIME_UPDATE.md
├── README_DIAGNOSTICS_MCP_FIX.md
├── REBUILD_CHANGELOG.md
├── REBUILD_NOTES.md
├── SECURITY.md
├── SUBMISSION_DEMO.md
├── LICENSE
└── README.md
```

---

# 🛠️ Technology Stack

| Area | Technology |
|---|---|
| Frontend | React + TypeScript |
| Build | Vite |
| Backend | Python + FastAPI |
| AI | Google Gemini |
| Agent Framework | Google ADK |
| Agent Observability | Grafana MCP |
| MCP Transport | Streamable HTTP |
| Observability | OpenTelemetry |
| Traces | Grafana Tempo |
| Logs | Grafana Loki |
| Metrics | Prometheus |
| Alerting | Grafana Alerting |
| Video | FFmpeg |
| Computer Vision | OpenCV |
| Cloud Storage | Google Cloud Storage |
| Cloud Runtime | Google Cloud Run |
| Observability Platform | Grafana Cloud |

---

# ⚙️ Local Development

## Prerequisites

You will need:

- Python 3.11+
- Node.js
- npm
- FFmpeg
- Google Cloud credentials
- Gemini API credentials
- Grafana Cloud credentials/configuration if using the live MCP path

---

# 1. Clone the Repository

```bash
git clone https://github.com/diyashah2914/Thats-A-Wrap.git
cd Thats-A-Wrap
```

---

# 2. Backend Environment

Create the local backend environment:

```bash
cd backend
python -m venv .venv
```

## Windows

```powershell
.venv\Scripts\Activate.ps1
```

## macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file from:

```text
backend/.env.example
```

Do **not** commit your `.env`.

---

# 3. Start the Backend

From the project root, the included Windows helper can be used:

```powershell
.\run-backend.bat
```

Or run FastAPI directly:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

---

# 4. Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server will provide the frontend URL.

---

# 🔐 Environment Variables

The exact configuration is documented in:

```text
backend/.env.example
frontend/.env.example
grafana-mcp/.env.example
```

Typical backend configuration includes:

```text
GEMINI_API_KEY
GRAFANA_MCP_URL
GRAFANA_MCP_SERVER_TOKEN
GRAFANA_URL
OTEL_EXPORTER_OTLP_ENDPOINT
OTEL_EXPORTER_OTLP_HEADERS
GOOGLE_CLOUD_PROJECT
GCS_BUCKET
```

Use your own credentials.

## Never Commit

```text
.env
API keys
service-account credentials
MCP bearer tokens
Grafana service-account tokens
OTLP authentication headers
private certificates
```

The repository's `.gitignore` is configured to keep local secrets and development environments out of Git.

---

# 🧪 Verification

The project contains several verification utilities.

## Backend Import

```bash
python -c "from app.main import app; print('BACKEND OK')"
```

## Grafana MCP

```bash
python backend/verify_grafana_mcp.py
```

## Google Cloud

```bash
python backend/verify_google_cloud.py
```

## MCP Runtime Test

```bash
python backend/test_mcp_runtime.py
```

## Backend Diagnostics

```text
http://127.0.0.1:8000/diagnostics
```

## MCP Diagnostics

```text
http://127.0.0.1:8000/diagnostics/mcp
```

## Live MCP Observability

```text
http://127.0.0.1:8000/observability/mcp
```

---

# 📊 Demonstrating the Observability Pipeline

A strong demonstration should show the complete chain rather than only the frontend.

## Step 1 — Start the Backend

Confirm that the API is running.

## Step 2 — Open the Diagnostics Page

Show:

- Grafana MCP connected
- real MCP tool count
- Grafana datasources
- Tempo traces
- Loki logs
- alert state
- MCP tool activity

## Step 3 — Start a Production Scene

Run an actual scene through the workflow.

## Step 4 — Show Production Activity

The application should record scene/job activity.

## Step 5 — Show Grafana Loki

In Grafana Explore, select the Loki datasource and query:

```logql
{service_name="thats-a-wrap-backend"}
```

Or:

```logql
{service_name="thats-a-wrap-backend"} |= "post-production"
```

## Step 6 — Show Grafana Tempo

Search for:

```traceql
{ resource.service.name = "thats-a-wrap-backend" }
```

## Step 7 — Return to That's a Wrap!

The Diagnostics screen can show the corresponding runtime evidence.

## Step 8 — Show the Rendered Result

Demonstrate:

```text
Rendered MP4
     ↓
Quality Control
     ↓
Cloud Storage
```

This creates an end-to-end demonstration rather than a collection of disconnected technologies.

---

# 🏆 What Makes This Project Different?

There are many AI applications that can generate a response.

That's a Wrap! focuses on something different:

# AI That Can Be Investigated

The project connects AI orchestration to an actual production pipeline and then connects that pipeline to real observability infrastructure.

The result is a system where you can ask:

> **What did the AI do?**

> **What did the media pipeline do?**

> **Did the render actually happen?**

> **What telemetry exists?**

> **What did Grafana observe?**

> **Did MCP actually participate?**

And the application is designed to answer those questions with runtime evidence wherever possible.

---

# 🧩 Design Principles

## 1. Truthful Telemetry

No fake counters or invented operational state.

---

## 2. Deterministic Media Processing

Critical media operations remain deterministic and testable.

---

## 3. AI as an Orchestrator

Gemini/ADK can reason about production context without becoming the only source of truth.

---

## 4. Observable by Design

Telemetry is part of the architecture rather than something added at the end.

---

## 5. MCP as a Runtime Integration

Grafana MCP is actually invoked rather than simply mentioned in documentation.

---

## 6. Graceful Uncertainty

If the system cannot obtain evidence, it should report:

```text
No matching Grafana telemetry was returned.
```

rather than manufacture an answer.

---

# 🔒 Security

Secrets are intentionally excluded from the repository.

Before deploying your own instance:

1. Create your own Gemini API key.
2. Configure your own Grafana credentials.
3. Configure your own MCP server token.
4. Configure your own Google Cloud authentication.
5. Configure your own GCS bucket.
6. Keep `.env` files outside version control.
7. Rotate any credentials that may have been exposed during development.

See:

```text
SECURITY.md
```

for additional project-specific security information.

---

# 📚 Additional Documentation

The repository includes deeper documentation for different audiences.

| Document | Purpose |
|---|---|
| `SUBMISSION_DEMO.md` | Demo and presentation flow |
| `FINAL_DEMO_RUNTIME_UPDATE.md` | Final runtime implementation |
| `CLOUD_MCP_RUNTIME_UPDATE.md` | Cloud/MCP implementation notes |
| `README_DIAGNOSTICS_MCP_FIX.md` | Diagnostics/MCP troubleshooting |
| `CONTRACTS.md` | API/data contracts |
| `SECURITY.md` | Security guidance |
| `REBUILD_CHANGELOG.md` | Major implementation changes |
| `REBUILD_NOTES.md` | Rebuild notes |
| `REBUILD-NOTES.txt` | Additional rebuild information |

---

# 🎥 Demo Assets

For a polished presentation, the recommended screenshots include:

1. **Main That's a Wrap! dashboard**
2. **Scene production workflow**
3. **Diagnostics / MCP control room**
4. **Grafana Loki showing real backend logs**
5. **Grafana Tempo showing a real backend trace**
6. **Grafana MCP tool activity**
7. **Rendered scene output**
8. **GCS bucket containing actual rendered objects**

Recommended future structure:

```text
docs/
└── screenshots/
    ├── dashboard.png
    ├── production.png
    ├── diagnostics.png
    ├── grafana-loki.png
    ├── grafana-tempo.png
    ├── mcp-tools.png
    ├── rendered-output.png
    └── gcs-output.png
```

---

# 🗺️ Future Improvements

Potential future work includes:

- richer scene-level AI editing recommendations
- more advanced timeline editing
- additional media formats
- automated highlight detection
- stronger scene continuity analysis
- deeper GCS asset management
- richer Tempo trace correlation
- more granular job/scene observability
- production dashboards
- multi-user projects
- authentication and authorization
- deployment automation
- additional MCP capabilities

---

# 🎬 Demo Story

The project can be presented as a simple story:

```text
        🎥
   RAW FOOTAGE
        │
        ▼
   ┌───────────┐
   │ AI + ADK  │
   └─────┬─────┘
         │
         ▼
   ┌───────────┐
   │ MCP       │
   │ + Grafana │
   └─────┬─────┘
         │
         ▼
   ┌───────────┐
   │ FFmpeg    │
   │ Rendering │
   └─────┬─────┘
         │
         ▼
   ┌───────────┐
   │    QC     │
   └─────┬─────┘
         │
         ▼
   ┌───────────┐
   │    GCS    │
   └─────┬─────┘
         │
         ▼
   ┌─────────────────┐
   │ Grafana Cloud   │
   │                 │
   │ Loki + Tempo    │
   │ + Metrics       │
   └─────────────────┘
```

The key message:

> **The AI makes decisions. The media pipeline does the work. Grafana lets us prove what happened.**

---

# 🧭 System Responsibility Map

| Component | Responsibility |
|---|---|
| React | User interface |
| FastAPI | Application API |
| Gemini | AI reasoning |
| Google ADK | Agent orchestration |
| Grafana MCP | Runtime observability access |
| FFmpeg | Media rendering |
| OpenCV | Computer vision utilities |
| QC | Output validation |
| GCS | Cloud asset storage |
| OpenTelemetry | Telemetry instrumentation |
| Grafana Loki | Logs |
| Grafana Tempo | Traces |
| Prometheus | Metrics |
| Grafana Alerting | Operational alerts |
| Cloud Run | Cloud runtime |

---

# 💡 The Core Idea

That's a Wrap! is built around a simple architecture:

```text
             CREATIVE LAYER
                  │
                  ▼
        ┌──────────────────┐
        │ Gemini + ADK     │
        │ AI Orchestration │
        └────────┬─────────┘
                 │
                 ▼
           OBSERVABILITY
                 │
                 ▼
        ┌──────────────────┐
        │   Grafana MCP    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Grafana Cloud    │
        │ Loki / Tempo /   │
        │ Prometheus       │
        └──────────────────┘

             PRODUCTION LAYER
                  │
                  ▼
        ┌──────────────────┐
        │ Deterministic    │
        │ Media Workflow   │
        └────────┬─────────┘
                 │
          ┌──────┼──────┐
          ▼      ▼      ▼
       FFmpeg  OpenCV   QC
          │      │      │
          └──────┼──────┘
                 ▼
        ┌──────────────────┐
        │ Google Cloud     │
        │ Storage          │
        └──────────────────┘
```

---

# 🌟 The Philosophy

The project is ultimately about combining two things that are often treated separately:

```text
        CREATIVE AI
             +
       ENGINEERING
             +
      OBSERVABILITY
             =
      TRUSTWORTHY AI
```

AI can help create.

Deterministic systems can execute.

Observability can verify.

That's a Wrap! brings those three layers together.

---

# 👥 Project

## That's a Wrap!

An AI-assisted filmmaking and post-production platform built around:

> **Creativity + Automation + Real Media Processing + Observable AI**

---

# 📜 License

See [`LICENSE`](LICENSE) for licensing information.

---

# ⭐ Final Thought

That's a Wrap! explores a simple idea:

> **AI should not only be capable of doing things — it should be possible to understand what it actually did.**

🎬 **That's a Wrap!**
