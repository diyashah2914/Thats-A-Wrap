"""Verify the exact Grafana MCP server used by the ADK production agent.

Run from backend:
    python verify_grafana_mcp.py

This prints tool names only and never prints credentials.
"""

import asyncio

from app.mcp_grafana import GrafanaMCPClient, GrafanaMCPError


async def main() -> None:
    try:
        result = await GrafanaMCPClient().inspect()
    except GrafanaMCPError as exc:
        print(f"MCP CHECK FAILED: {exc}")
        raise SystemExit(1)

    print(f"MCP CONNECTED: {result.get('connected')}")
    print(f"TRANSPORT: {result.get('transport')}")
    print(f"TOOL COUNT: {result.get('tool_count')}")
    print("TOOLS:")
    for tool in result.get("tools", []):
        print(f"  - {tool}")


if __name__ == "__main__":
    asyncio.run(main())
