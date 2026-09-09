"""That's a Wrap! production orchestrator with Grafana Cloud MCP."""

import os
from google import genai
from google.adk.agents import Agent
from google.adk.models import Gemini

from google.adk.tools.mcp_tool import (
    McpToolset,
    StreamableHTTPConnectionParams,
)

from app.config import settings


MODEL = settings.gemini_model or "gemini-3.7-flash"

GRAFANA_URL = settings.grafana_url or os.getenv("GRAFANA_URL")

if not GRAFANA_URL:
    raise RuntimeError(
        "GRAFANA_URL must be configured for Grafana Cloud MCP"
    )


MCP_SERVER_TOKEN = (
    settings.grafana_mcp_server_token
    or os.getenv("GRAFANA_MCP_SERVER_TOKEN")
)

if not MCP_SERVER_TOKEN:
    raise RuntimeError(
        "GRAFANA_MCP_SERVER_TOKEN must be configured "
        "for Grafana MCP"
    )


grafana_headers = {
    "Authorization": f"Bearer {MCP_SERVER_TOKEN}",
    "Accept": "application/json, text/event-stream",
}


if settings.grafana_mcp_extra_headers:
    for item in settings.grafana_mcp_extra_headers.split(","):
        if ":" in item:
            key, value = item.split(":", 1)
            grafana_headers[key.strip()] = value.strip()


grafana_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=settings.grafana_mcp_url,
        headers=grafana_headers,
        timeout=settings.grafana_mcp_timeout_seconds,
        sse_read_timeout=(
            settings.grafana_mcp_sse_read_timeout_seconds
        ),
    ),
    tool_name_prefix="grafana_",
)


def director_tool(script: str) -> str:
    """Analyse a screenplay and return scene-breakdown instructions."""

    return (
        "Analyse screenplay into ordered scenes. "
        f"Script length: {len(script)} characters."
    )


def editor_tool(scene_id: str, takes: str) -> str:
    """Evaluate available takes and return an editing recommendation."""

    return (
        f"Evaluate takes {takes} for {scene_id} "
        "and choose the strongest performance."
    )


def production_tool(
    job_status: str,
    error: str = "",
) -> str:
    """Inspect processing status and decide whether a failed job should retry."""

    if job_status == "FAILED":
        return (
            "Retry the failed job after diagnosing: "
            f"{error or 'unknown error'}"
        )

    return "No recovery required."


if not settings.gemini_api_key:
    raise RuntimeError(
        "GEMINI_API_KEY must be configured for ADK orchestration"
    )

gemini_client = genai.Client(
    api_key=settings.gemini_api_key
)

root_agent = Agent(
    name="production_orchestrator",
    model=Gemini(model=MODEL, client=gemini_client,),
    instruction="""
You are the Production Orchestrator for That's a Wrap!.

You coordinate Director, Editor, Sound, Music, Colour, VFX,
Post Production and QC.

Grafana Cloud MCP is a REAL runtime observability source.

IMPORTANT:

When the user asks about:

- processing status
- pipeline failures
- scene processing
- QC
- FFmpeg
- latency
- backend execution
- agent execution
- traces
- logs
- production telemetry

you MUST use the available Grafana MCP tools before answering.

Do not infer observability data from memory.

Do not fabricate telemetry.

If a Grafana MCP tool returns no matching data, explicitly say that
no matching data was found.

If Grafana MCP is unavailable, explicitly report that it is unavailable.

When investigating traces, prefer Tempo-related MCP tools when exposed.

When investigating application logs, use Loki-related MCP tools when exposed.

When investigating metrics, use Prometheus-related MCP tools when exposed.

When investigating dashboards, use dashboard-related MCP tools when exposed.

For any observability question, tool invocation is preferred over
a speculative answer.

Never claim that an MCP tool was used unless the tool actually returned
a result.

Never claim a trace exists unless Grafana returned it.

Never claim media processing succeeded unless the actual processing
worker reports success.

Correlate production decisions with actual observability evidence
whenever that evidence is available.
""",
    tools=[
        director_tool,
        editor_tool,
        production_tool,
        grafana_mcp,
    ],
)