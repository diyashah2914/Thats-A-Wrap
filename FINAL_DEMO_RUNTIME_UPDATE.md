# Final demo runtime update

## What changed

- Added a live `/observability/mcp` API backed by the deployed Grafana MCP server.
- The dashboard now shows real MCP tool activity, Grafana datasources, Loki logs, Tempo traces, alert rules, queries and timestamps.
- Grafana MCP dashboard data is cached briefly to keep polling responsive while remaining live.
- Multiple Grafana MCP reads share one Streamable HTTP session where possible.
- `/diagnostics/mcp` now uses the real MCP `tools/list` handshake and no longer calls the removed `inspect()` implementation.
- `verify_grafana_mcp.py` remains compatible through the `inspect()` alias.
- ADK/Gemini orchestration is still real and uses the remote Grafana MCP, but is now run concurrently with the deterministic media worker so Gemini/MCP latency does not hold up FFmpeg.
- The ADK prompt is deliberately limited to at most two read-only MCP calls for a production scene to reduce Gemini token usage and demo latency.
- FFmpeg demo defaults use `superfast` encoding, CRF 21 and automatic threading. Override with `FFMPEG_PRESET` and `FFMPEG_CRF` if desired.
- Frontend observability polling is faster and does not repeatedly perform an uncached 81-tool MCP discovery.

## Truthfulness rules

The UI does not invent telemetry. Empty Grafana results are rendered as "No data"; unavailable services are rendered as unavailable; successful MCP calls are shown only when the MCP server actually returned successfully.

## Before running

Copy your existing local `backend/.env` into this package. Do not commit or share that file. The generated package intentionally does not include `.env`.

Your existing `.venv` can be reused, or recreate it from `backend/requirements.txt`.

## Demo flow

1. Start backend.
2. Start frontend.
3. Open a project and process a real scene.
4. Open Diagnostics.
5. Show the `LIVE GRAFANA MCP / RUNTIME EVIDENCE` section.
6. Show actual Loki events and Tempo traces.
7. Open Grafana Explore from the link and reproduce the same Loki/Tempo evidence.
8. Open the real GCS object/artifact when demonstrating cloud storage.
