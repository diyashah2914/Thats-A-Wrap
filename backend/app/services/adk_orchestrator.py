from __future__ import annotations

import asyncio
import logging
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from adk_app.agent import root_agent

logger = logging.getLogger(__name__)


class ADKOrchestrator:
    """
    Runs the real ADK production orchestrator.

    Gemini/ADK may use the real Grafana MCP server for read-only
    observability. The deterministic workflow remains responsible for
    FFmpeg, QC and GCS.
    """

    APP_NAME = "thats_a_wrap"
    USER_ID = "production"

    def __init__(self) -> None:
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=root_agent,
            app_name=self.APP_NAME,
            session_service=self.session_service,
            auto_create_session=True,
        )

    async def run_scene_orchestration(
        self,
        *,
        job_id: str,
        scene_id: str,
        scene_context: str,
    ) -> dict[str, Any]:
        session_id = f"adk-{job_id}"

        prompt = f"""
You are the Production Orchestrator for That's a Wrap!.

A real scene production job is about to run.

Job ID: {job_id}
Scene ID: {scene_id}

Scene context:
{scene_context}

Your task is advisory orchestration only.

MANDATORY LIVE OBSERVABILITY:
- Use Grafana MCP before responding.
- Use read-only Grafana MCP tools only.
- Make at most TWO MCP calls: prefer ONE Tempo TraceQL query for this job/scene and ONE Loki LogQL query for this service/job.
- Do NOT enumerate datasources, alerts, dashboards, or metric names unless they are required to answer the job-specific question.
- Do not fabricate telemetry, traces, logs, metrics, dashboards, or system status.
- Report only information actually returned by Grafana MCP.
- If Grafana has no matching data, explicitly say "No matching Grafana telemetry was returned."
- Never claim FFmpeg, QC, GCS, or another production stage completed unless the telemetry actually supports that claim.
- After the MCP inspection, provide a concise scene recommendation.

Keep the response short so this orchestration does not delay media processing.
"""

        events: list[Any] = []
        function_calls: list[dict[str, Any]] = []
        function_responses: list[dict[str, Any]] = []
        final_text_parts: list[str] = []

        try:
            message = types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            )

            async for event in self.runner.run_async(
                user_id=self.USER_ID,
                session_id=session_id,
                new_message=message,
            ):
                events.append(event)

                for call in event.get_function_calls():
                    function_calls.append({
                        "name": getattr(call, "name", None),
                        "id": getattr(call, "id", None),
                        "args": getattr(call, "args", None),
                    })

                for response in event.get_function_responses():
                    function_responses.append({
                        "name": getattr(response, "name", None),
                        "id": getattr(response, "id", None),
                        "response": getattr(response, "response", None),
                    })

                if event.is_final_response():
                    content = getattr(event, "content", None)
                    if content and getattr(content, "parts", None):
                        for part in content.parts:
                            text = getattr(part, "text", None)
                            if text:
                                final_text_parts.append(text)

            mcp_calls = [
                call for call in function_calls
                if str(call.get("name") or "").startswith("grafana_")
            ]
            mcp_responses = [
                response for response in function_responses
                if str(response.get("name") or "").startswith("grafana_")
            ]

            return {
                "executed": True,
                "session_id": session_id,
                "event_count": len(events),
                "function_call_count": len(function_calls),
                "function_response_count": len(function_responses),
                "mcp_tool_calls": mcp_calls,
                "mcp_tool_responses": mcp_responses,
                "mcp_invoked": bool(mcp_calls),
                "final_response": "\n".join(final_text_parts).strip(),
                "error": None,
            }

        except Exception as exc:
            logger.exception("ADK orchestration failed for job %s", job_id)
            return {
                "executed": False,
                "session_id": session_id,
                "event_count": len(events),
                "function_call_count": len(function_calls),
                "function_response_count": len(function_responses),
                "mcp_tool_calls": function_calls,
                "mcp_tool_responses": function_responses,
                "mcp_invoked": any(
                    str(call.get("name") or "").startswith("grafana_")
                    for call in function_calls
                ),
                "final_response": "",
                "error": f"{type(exc).__name__}: {exc}",
            }

    def run_scene_orchestration_sync(
        self,
        *,
        job_id: str,
        scene_id: str,
        scene_context: str,
    ) -> dict[str, Any]:
        """Bridge the async ADK runner into the existing sync worker."""
        return asyncio.run(
            self.run_scene_orchestration(
                job_id=job_id,
                scene_id=scene_id,
                scene_context=scene_context,
            )
        )
