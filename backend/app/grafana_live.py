"""Small, read-only Grafana/Tempo bridge used by the web UI.

Secrets stay server-side. The browser receives only sanitized trace summaries.
"""
from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings


_SAFE_SPAN_NAMES = {
    "scene_post_production_pipeline",
    "media_validation",
    "ai_editor_take_selection",
    "ai_specialist_planning",
    "ai_music_supervision",
    "ai_sound_specialist",
    "ai_colour_specialist",
    "ai_color_specialist",
    "ai_vfx_specialist",
    "ai_post_production_direction",
    "ai_vfx_direction",
    "ai_cinematography_direction",
    "ai_color_direction",
    "ai_audio_music_direction",
    "ffmpeg_scene_render",
    "ffmpeg_command",
    "scene_qc",
    "ffprobe_quality_control",
    "production_agent_assembly_plan",
    "final_film_assembly",
    "gemini_structured_generation",
}


class GrafanaLiveError(RuntimeError):
    pass


class GrafanaLiveClient:
    def __init__(self) -> None:
        self._tempo_uid: str | None = settings.grafana_tempo_datasource_uid
        self._tempo_uid_expires = 0.0

    @property
    def configured(self) -> bool:
        return bool(settings.grafana_url and settings.grafana_observability_token)

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {settings.grafana_observability_token}"
        headers.setdefault("Accept", "application/json")
        timeout = httpx.Timeout(connect=4.0, read=8.0, write=4.0, pool=4.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            try:
                response = await client.request(method, url, headers=headers, **kwargs)
            except httpx.HTTPError as exc:
                raise GrafanaLiveError("Grafana telemetry request failed.") from exc
        return response

    async def _datasource_uid(self) -> str:
        if self._tempo_uid and time.monotonic() < self._tempo_uid_expires:
            return self._tempo_uid
        if self._tempo_uid and self._tempo_uid_expires == 0:
            # An explicitly configured UID is trusted and avoids a metadata lookup.
            self._tempo_uid_expires = time.monotonic() + 3600
            return self._tempo_uid
        if not settings.grafana_url:
            raise GrafanaLiveError("Grafana URL is not configured.")
        response = await self._request("GET", f"{settings.grafana_url.rstrip('/')}/api/datasources")
        if response.status_code != 200:
            raise GrafanaLiveError("Grafana datasource discovery is unavailable.")
        try:
            datasources = response.json()
        except ValueError as exc:
            raise GrafanaLiveError("Grafana returned an invalid datasource response.") from exc
        candidates = [
            ds for ds in datasources
            if str(ds.get("type", "")).lower() == "tempo"
            or str(ds.get("name", "")).lower() == settings.grafana_tempo_datasource_name.lower()
        ]
        if not candidates or not candidates[0].get("uid"):
            raise GrafanaLiveError("No Tempo datasource was found in Grafana.")
        self._tempo_uid = str(candidates[0]["uid"])
        self._tempo_uid_expires = time.monotonic() + 3600
        return self._tempo_uid

    @staticmethod
    def _safe_name(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        value = value.strip()
        return value if value in _SAFE_SPAN_NAMES else None

    @classmethod
    def _extract_span_names(cls, payload: Any) -> list[str]:
        names: list[str] = []
        def walk(value: Any) -> None:
            if isinstance(value, dict):
                if "name" in value:
                    name = cls._safe_name(value.get("name"))
                    if name and name not in names:
                        names.append(name)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(payload)
        return names[:24]

    async def live_traces(self, minutes: int | None = None, limit: int | None = None) -> dict[str, Any]:
        if not self.configured:
            return {"connected": False, "reason": "Grafana live telemetry is not configured.", "traces": []}
        minutes = max(1, min(int(minutes or settings.grafana_live_window_minutes), 30))
        limit = max(1, min(int(limit or settings.grafana_live_limit), 12))
        uid = await self._datasource_uid()
        now = int(time.time())
        start = now - minutes * 60
        base = settings.grafana_url.rstrip("/")
        proxy = f"{base}/api/datasources/proxy/uid/{uid}/api/search"
        params = {
            "q": '{ resource.service.name = "thats-a-wrap-backend" }',
            "start": str(start),
            "end": str(now),
            "limit": str(limit),
        }
        response = await self._request("GET", proxy, params=params)
        if response.status_code in (401, 403):
            raise GrafanaLiveError("Grafana telemetry token is not authorized to query Tempo.")
        if response.status_code >= 400:
            raise GrafanaLiveError(f"Grafana Tempo query returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GrafanaLiveError("Grafana Tempo returned an invalid search response.") from exc
        traces = payload.get("traces", []) if isinstance(payload, dict) else []
        if not isinstance(traces, list):
            traces = []

        async def enrich(item: dict[str, Any]) -> dict[str, Any]:
            trace_id = str(item.get("traceID", ""))
            span_names = self._extract_span_names(item.get("spanSets", []))
            if trace_id and not span_names:
                try:
                    detail = await self._request("GET", f"{proxy.rsplit('/api/search', 1)[0]}/api/traces/{trace_id}")
                    if detail.status_code == 200:
                        span_names = self._extract_span_names(detail.json())
                except GrafanaLiveError:
                    pass
            return {
                "trace_id": trace_id,
                "root_service": str(item.get("rootServiceName", ""))[:100],
                "root_operation": str(item.get("rootTraceName", ""))[:160],
                "start_time": str(item.get("startTimeUnixNano", ""))[:30],
                "duration_ms": round(float(item.get("durationMs", 0) or 0), 2),
                "agents_and_stages": span_names,
            }

        enriched = await asyncio.gather(*(enrich(item) for item in traces[:limit]))
        return {
            "connected": True,
            "source": "Grafana Cloud / Tempo",
            "window_minutes": minutes,
            "traces": enriched,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
