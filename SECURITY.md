# Security and secrets

## Never commit secrets

Keep real credentials in `backend/.env` locally or in your deployment platform's secret/environment configuration. The repository contains only `backend/.env.example` and `frontend/.env.example` templates.

Never place `GEMINI_API_KEY`, `GRAFANA_OBSERVABILITY_TOKEN`, `OTEL_EXPORTER_OTLP_HEADERS`, or MCP tokens in React code, `VITE_*` variables, screenshots, Git history, or client-visible JSON.

## Grafana architecture

The browser calls FastAPI diagnostics/telemetry endpoints. Grafana credentials never reach React. The optional `/observability/live` endpoint returns only sanitized trace summaries from a server-side Grafana Tempo query. The Grafana token never reaches the browser.

Use a dedicated read/query credential for the website. Do not reuse the MCP credential if a separate least-privilege credential can be created. The application only needs read/query access to the Tempo datasource; it does not need datasource write/delete permissions.

If using a Grafana service account, Grafana documents `datasources:read` for listing datasources and `datasources:query` for querying them. Scope those permissions to the specific Tempo datasource where your Grafana setup supports scoped permissions.

## Deployment

For Cloud Run or another hosting platform, inject secrets as runtime environment variables/secrets rather than baking them into the image. Restrict `ALLOWED_ORIGINS` to the real deployed frontend origin.

## Browser/API hardening

The live telemetry endpoint returns only an allow-listed set of span names, operation names, timings, and trace IDs. It does not proxy arbitrary Grafana URLs or return raw trace attributes. Requests have short upstream timeouts and bounded time windows/results.


## MCP credential separation

The official Grafana MCP server uses `GRAFANA_SERVICE_ACCOUNT_TOKEN`. The backend uses `GRAFANA_OBSERVABILITY_TOKEN` only for its optional server-side Tempo preview. These credentials should not be reused unless you intentionally accept the broader permission set.

If the MCP HTTP server is exposed beyond localhost, set `MCP_GRAFANA_SERVER_TOKEN` / `--server-auth-token` as well.
