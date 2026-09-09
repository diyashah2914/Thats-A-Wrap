# Observability rebuild v3 — change manifest

## Primary fixes

1. **`.env` loading bug fixed**
   - `backend/app/config.py` uses an absolute backend `.env` path.
   - OTLP/Grafana configuration is read through the Settings object rather than `os.getenv()`.
   - This fixes the exact symptom where `load_dotenv()` made the Gemini key visible but `/diagnostics` still said Grafana was missing.

2. **OTLP 401 path fixed**
   - `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` are loaded from Settings.
   - URL-encoded header values are decoded before being passed to the exporter.
   - The app no longer silently creates a localhost exporter when OTLP is not configured.
   - Diagnostics includes an OTLP auth probe that distinguishes 401 from a normal GET/POST method mismatch.

3. **Logs added to OTLP**
   - Structured application activity is exported through `/v1/logs` when OTLP is configured.
   - This gives Grafana/Loki a real application log stream alongside traces.

4. **Detailed persistent diagnostic events**
   - `backend/app/store.py` persists up to 1,000 diagnostic events.
   - `/diagnostics/activity` exposes sanitized event metadata.

5. **Real Grafana MCP inspection**
   - `backend/app/mcp_grafana.py` uses the official Python MCP client to connect to the configured Grafana MCP SSE server.
   - `/diagnostics/mcp` lists the real tools exposed by the MCP server.
   - The full diagnostics run checks for Prometheus, Loki, dashboards, incident/Sift and Tempo-proxy tool coverage.

6. **Local full observability stack**
   - Prometheus + Loki + Tempo + Grafana are included in `observability/docker-compose.yml`.
   - Tempo OTLP receivers and Tempo MCP are enabled.
   - Grafana provisions Prometheus, Loki and Tempo datasources.

7. **Diagnostics UI rebuilt**
   - Runtime health
   - All agents and latest run status
   - Job counts and failures
   - OTLP configuration
   - Grafana API health
   - MCP health and actual tool coverage
   - Detailed event stream with filters
   - Recovery controls
   - MCP investigation playbook for PromQL, LogQL, dashboards, incidents and TraceQL

## Intentionally not included

- `backend/.env` — secrets are never included.
- `.git` — the rebuilt package is source-only and avoids carrying credentials or old history.
- `backend/media/input`, `backend/media/output`, `backend/media/state.json` — these are generated/runtime data. Reconnect or copy your media separately. Bundled original demo music remains.

## Important credential split

- `GRAFANA_OBSERVABILITY_TOKEN` → optional backend read/query credential for the sanitized Tempo preview.
- `GRAFANA_SERVICE_ACCOUNT_TOKEN` → Grafana MCP server credential.
- `MCP_GRAFANA_SERVER_TOKEN` → optional caller-auth token for the MCP HTTP server.
- `OTEL_EXPORTER_OTLP_HEADERS` → Grafana Cloud OTLP ingestion credential.

Do not reuse credentials unless you deliberately accept the broader permissions.
