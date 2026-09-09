# Cloud MCP runtime update

Production Grafana MCP is deployed on Cloud Run and consumed over Streamable HTTP:

- MCP: https://grafana-mcp-450541203194.us-central1.run.app/mcp
- Grafana: https://zealousgondola816.grafana.net
- Explore/Tempo: https://zealousgondola816.grafana.net/explore
- Dashboards: https://zealousgondola816.grafana.net/dashboards

The ADK agent and backend diagnostics use the remote MCP endpoint. `/diagnostics/mcp` performs a real MCP session and a read-only `search_dashboards` invocation; the frontend separates MCP session connectivity from successful tool invocation.

Job state now carries stage/progress/message/error code, and diagnostic events are available as a live log stream. FFmpeg audio mixing explicitly pads/trims/resamples to the target duration, while QC records stream durations and applies a 0.25s alignment tolerance.

The real backend `.env` is intentionally excluded. Use `backend/.env.example` and deployment/Secret Manager configuration.
