"""Live Grafana MCP observability aggregation for the dashboard."""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from app.mcp_grafana import GrafanaMCPClient


def _json_text(result: Any) -> Any:
    if result is None or isinstance(result, Exception):
        return None
    content = getattr(result, "content", None)
    if not content:
        return None
    for item in content:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            return json.loads(text)
        except (TypeError, ValueError):
            return text
    return None


def _find_tool(tools: list[dict[str, Any]], needle: str) -> str | None:
    for tool in tools:
        name = str(tool.get("name", ""))
        if name == needle or name.endswith(needle) or needle in name:
            return name
    return None


class MCPObservability:
    """Cached, read-only Grafana MCP data for the web UI."""

    def __init__(self, client: GrafanaMCPClient) -> None:
        self.client = client
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def snapshot(
        self,
        *,
        job_id: str | None = None,
        scene_id: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        cache_key = f"{job_id or ''}:{scene_id or ''}"
        if not force:
            cached = self._cache.get(cache_key)
            if cached and time.monotonic() - cached[0] < 8:
                return cached[1]

        async with self._lock:
            if not force:
                cached = self._cache.get(cache_key)
                if cached and time.monotonic() - cached[0] < 8:
                    return cached[1]

            checked_at = datetime.now(timezone.utc).isoformat()
            try:
                tools = await self.client.list_tools()
            except Exception as exc:
                result = {
                    "connected": False,
                    "source": "Grafana MCP",
                    "checked_at": checked_at,
                    "error": f"{type(exc).__name__}: {exc}",
                    "tool_count": 0,
                    "datasources": [],
                    "logs": [],
                    "traces": [],
                    "alerts": [],
                    "tool_activity": [],
                    "evidence": [],
                }
                self._cache[cache_key] = (time.monotonic(), result)
                return result

            tool_activity: list[dict[str, Any]] = []
            evidence: list[dict[str, Any]] = []

            def add_activity(tool: str | None, status: str, arguments: dict[str, Any]) -> None:
                tool_activity.append({
                    "tool": tool or "unavailable",
                    "status": status,
                    "arguments": arguments,
                })

            def add_evidence(label: str, tool: str | None, arguments: dict[str, Any], status: str) -> None:
                evidence.append({
                    "label": label,
                    "tool": tool or "unavailable",
                    "arguments": arguments,
                    "status": status,
                })

            # 1) Datasources establish the real backend UIDs.
            ds_tool = _find_tool(tools, "list_datasources")
            datasources: list[dict[str, Any]] = []
            if ds_tool:
                try:
                    ds_results = await self.client.call_tools([(ds_tool, {})])
                    ds_result = ds_results.get(ds_tool)
                    ds_payload = _json_text(ds_result)
                    if isinstance(ds_payload, dict):
                        ds_payload = ds_payload.get("data", ds_payload.get("datasources", []))
                    if isinstance(ds_payload, list):
                        datasources = [x for x in ds_payload if isinstance(x, dict)]
                    status = "SUCCESS" if ds_result is not None and not getattr(ds_result, "isError", False) else "ERROR"
                    add_activity(ds_tool, status, {})
                    add_evidence("Grafana datasources", ds_tool, {}, status)
                except Exception as exc:
                    add_activity(ds_tool, "ERROR", {"error": f"{type(exc).__name__}: {exc}"})
            else:
                add_activity("list_datasources", "UNAVAILABLE", {})

            tempo_uid = None
            loki_uid = None
            for ds in datasources:
                dtype = str(ds.get("type", "")).lower()
                name = str(ds.get("name", "")).lower()
                uid = ds.get("uid") or ds.get("datasourceUid")
                if dtype == "tempo" and uid == "grafanacloud-traces":
                    tempo_uid = uid
                if dtype == "loki" and uid == "grafanacloud-logs":
                    loki_uid = uid

            # 2) Query logs, traces and alerts through ONE MCP session.
            # Keep Loki service-wide so a job-scoped dashboard still shows the
            # real production events even when job_id is stored in structured
            # metadata rather than the rendered log line. Tempo remains
            # job/scene-scoped below.
            logql = '{service_name="thats-a-wrap-backend"}'

            trace_query = '{ resource.service.name = "thats-a-wrap-backend" }'
            if job_id or scene_id:
                clauses = []
                if job_id:
                    clauses.append(f'span.job_id = "{job_id}"')
                if scene_id:
                    clauses.append(f'span.scene_id = "{scene_id}"')
                trace_query = "{ " + " || ".join(clauses) + " }"

            log_tool = _find_tool(tools, "query_loki_logs")
            trace_tool = _find_tool(tools, "tempo_traceql-search")
            alert_tool = _find_tool(tools, "alerting_manage_rules")

            batch_calls: list[tuple[str, dict[str, Any]]] = []
            labels: list[tuple[str, str, dict[str, Any]]] = []

            if log_tool:
                args = {"logql": logql}
                if loki_uid:
                    args["datasourceUid"] = loki_uid
                batch_calls.append((log_tool, args))
                labels.append(("logs", log_tool, args))
            else:
                add_activity("query_loki_logs", "UNAVAILABLE", {})

            if trace_tool:
                args = {"query": trace_query}
                if tempo_uid:
                    args["datasourceUid"] = tempo_uid
                batch_calls.append((trace_tool, args))
                labels.append(("traces", trace_tool, args))
            else:
                add_activity("tempo_traceql-search", "UNAVAILABLE", {})

            if alert_tool:
                args = {"operation": "list", "rule_limit": 10}
                batch_calls.append((alert_tool, args))
                labels.append(("alerts", alert_tool, args))
            else:
                add_activity("alerting_manage_rules", "UNAVAILABLE", {})

            batch_results: dict[str, Any] = {}
            if batch_calls:
                try:
                    batch_results = await self.client.call_tools(batch_calls)
                except Exception as exc:
                    for _, tool_name, args in labels:
                        add_activity(tool_name, "ERROR", {**args, "error": f"{type(exc).__name__}: {exc}"})
                else:
                    for label, tool_name, args in labels:
                        result = batch_results.get(tool_name)
                        ok = result is not None and not getattr(result, "isError", False)
                        status = "SUCCESS" if ok else "ERROR"
                        add_activity(tool_name, status, args)
                        add_evidence(
                            {"logs": "Loki application logs", "traces": "Tempo distributed traces", "alerts": "Grafana alert rules"}[label],
                            tool_name,
                            args,
                            status,
                        )

            # Parse logs.
            logs_payload = _json_text(batch_results.get(log_tool)) if log_tool else {}
            logs = []
            log_metadata = {}
            if isinstance(logs_payload, dict):
                logs = logs_payload.get("data", []) or []
                log_metadata = logs_payload.get("metadata", {}) or {}
            elif isinstance(logs_payload, list):
                logs = logs_payload
            if not isinstance(logs, list):
                logs = []

            # Parse traces.
            trace_payload = _json_text(batch_results.get(trace_tool)) if trace_tool else {}
            if isinstance(trace_payload, dict):
                traces = trace_payload.get("traces", trace_payload.get("data", [])) or []
            elif isinstance(trace_payload, list):
                traces = trace_payload
            else:
                traces = []
            if not isinstance(traces, list):
                traces = []

            # Parse alert rules.
            alerts_payload = _json_text(batch_results.get(alert_tool)) if alert_tool else []
            if isinstance(alerts_payload, dict):
                alerts = alerts_payload.get("rules", alerts_payload.get("data", [])) or []
            elif isinstance(alerts_payload, list):
                alerts = alerts_payload
            else:
                alerts = []
            if not isinstance(alerts, list):
                alerts = []

            normalized_logs = []
            for item in logs[:12]:
                if not isinstance(item, dict):
                    continue
                normalized_logs.append({
                    "timestamp": item.get("timestamp"),
                    "line": item.get("line"),
                    "labels": item.get("labels", {}),
                    "structuredMetadata": item.get("structuredMetadata", {}),
                })

            normalized_traces = []
            for item in traces[:12]:
                if not isinstance(item, dict):
                    continue
                span_set = item.get("spanSet")
                normalized_traces.append({
                    "trace_id": item.get("traceID") or item.get("traceId") or item.get("trace_id"),
                    "root_service": item.get("rootServiceName"),
                    "root_operation": item.get("rootTraceName"),
                    "start_time": item.get("startTimeUnixNano"),
                    "duration_ms": item.get("durationMs"),
                    "service_stats": item.get("serviceStats", {}),
                    "matched": span_set.get("matched") if isinstance(span_set, dict) else None,
                })

            normalized_alerts = []
            for item in alerts[:10]:
                if not isinstance(item, dict):
                    continue
                normalized_alerts.append({
                    "uid": item.get("uid") or item.get("id"),
                    "name": item.get("name") or item.get("alertname") or item.get("title"),
                    "state": item.get("state") or item.get("status") or item.get("alertstate"),
                    "health": item.get("health"),
                    "folder": item.get("folder") or item.get("grafana_folder"),
                })

            result = {
                "connected": True,
                "source": "Grafana Cloud via Grafana MCP",
                "checked_at": checked_at,
                "tool_count": len(tools),
                "datasources": [
                    {
                        "uid": ds.get("uid") or ds.get("datasourceUid"),
                        "name": ds.get("name"),
                        "type": ds.get("type"),
                        "isDefault": ds.get("isDefault"),
                    }
                    for ds in datasources
                ],
                "logs": normalized_logs,
                "log_metadata": log_metadata,
                "traces": normalized_traces,
                "alerts": normalized_alerts,
                "tool_activity": tool_activity,
                "evidence": evidence,
                "queries": {"loki": logql, "tempo": trace_query},
                "job_id": job_id,
                "scene_id": scene_id,
                "error": None,
            }
            self._cache[cache_key] = (time.monotonic(), result)
            return result


mcp_observability: MCPObservability | None = None
