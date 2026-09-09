# Grafana MCP integration

The production Grafana MCP server is the official `grafana/mcp-grafana` image deployed on Google Cloud Run.

- MCP endpoint: `https://grafana-mcp-450541203194.us-central1.run.app/mcp`
- Transport: Streamable HTTP
- Grafana Cloud: `https://zealousgondola816.grafana.net`
- Explore/Tempo: `https://zealousgondola816.grafana.net/explore`
- Dashboards: `https://zealousgondola816.grafana.net/dashboards`

The ADK agent and backend diagnostics connect directly to the Cloud Run endpoint. `/diagnostics/mcp` verifies an actual MCP session and performs a read-only `search_dashboards` tool call before the UI reports a verified MCP invocation.

Required deployment settings are `GRAFANA_MCP_URL`, `GRAFANA_SERVICE_ACCOUNT_TOKEN`, and `GRAFANA_URL`. Never commit the real token.
