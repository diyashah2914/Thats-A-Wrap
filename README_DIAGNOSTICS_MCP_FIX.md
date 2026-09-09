# That's a Wrap — Diagnostics / MCP Fix Patch

This patch is based directly on the uploaded `That's-A-Wrap-SUBMISSION-CONTINGENCY (3).zip`.

## Replace only these files

- `backend/app/main.py`
- `frontend/src/pages/Diagnostics.tsx`
- `frontend/src/App.css`

Your existing `backend/.env`, `backend/media/`, project state, agents, and the rest of the application are intentionally NOT included.

## What this fixes

### Diagnostics no longer treats configuration as runtime failure

It now separates:
- configuration
- connectivity
- authentication rejection
- optional components that are not running

It also no longer labels the deterministic AI mode as a mysterious "FALLBACK" system. If Gemini is not active, it explicitly says deterministic mode is configured.

### FFmpeg

The diagnostics label is now "Media engine" and only reports PASS when both ffmpeg and ffprobe are available to the backend. Otherwise it reports a warning instead of claiming the whole application is broken.

### Grafana

Grafana MCP is treated as the primary Grafana integration. The optional direct Grafana API is not reported as a failure when its separate read token is not configured.

### MCP

The diagnostics page no longer fails/stales just because the MCP server is offline. MCP status is independent.

The backend now correctly creates the Grafana MCP client and reports actual MCP tool discovery when the MCP SSE server is running.

### OTLP 401

The diagnostics now distinguishes:
- OTLP endpoint configured
- OTLP auth configured
- OTLP gateway reachable
- HTTP 401 authentication rejection

A 401 means Grafana Cloud received the request but rejected the credential. That cannot be repaired by frontend code. The Grafana Cloud OTLP credential must be valid for the stack.

The current uploaded `.env` contains a structurally valid Basic Authorization value (`instance-id:glc_...`), so if the gateway still returns 401, the token itself is being rejected (for example revoked/expired/wrong stack). The diagnostics now says exactly that instead of falsely saying the auth header is missing.

## Important

Do NOT replace your real `.env` with an example file.

After copying these three files, restart the backend and rebuild/restart the frontend so the new diagnostics code is loaded.
