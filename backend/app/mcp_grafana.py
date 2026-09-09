from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings


class GrafanaMCPError(Exception):
    """Raised when the Grafana MCP connection or operation fails."""


class GrafanaMCPClient:
    """
    Deterministic client for the remote Grafana MCP server.

    This is intentionally separate from ADK's McpToolset:
    - this client proves the remote MCP server is reachable and callable
    - McpToolset exposes the same MCP server to the Gemini agent
    """

    def __init__(self) -> None:
        self.url = settings.grafana_mcp_url.rstrip("/")
        self.token = settings.grafana_mcp_server_token
        self._tools_cache: list[dict[str, Any]] | None = None
        self._tools_cache_at = 0.0

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=settings.grafana_mcp_timeout_seconds,
            write=settings.grafana_mcp_timeout_seconds,
            pool=settings.grafana_mcp_timeout_seconds,
            read=settings.grafana_mcp_sse_read_timeout_seconds,
        )

    async def _imports(self):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        return ClientSession, streamable_http_client

    async def _session(self):
        ClientSession, streamable_http_client = await self._imports()
        http_client = httpx.AsyncClient(
            headers=self._headers(),
            timeout=self._timeout(),
        )
        transport = streamable_http_client(
            self.url,
            http_client=http_client,
        )
        return ClientSession, http_client, transport

    async def list_tools(self, *, force: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if (
            not force
            and self._tools_cache is not None
            and now - self._tools_cache_at < 30
        ):
            return self._tools_cache

        ClientSession, http_client, transport = await self._session()
        try:
            async with http_client:
                async with transport as streams:
                    read_stream, write_stream, _ = streams
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        tools = [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema,
                            }
                            for tool in result.tools
                        ]
                        self._tools_cache = tools
                        self._tools_cache_at = time.monotonic()
                        return tools
        except Exception as exc:
            raise GrafanaMCPError(
                f"{type(exc).__name__}: {exc}"
            ) from exc

    async def call_tools(
        self,
        calls: list[tuple[str, dict[str, Any]]],
    ) -> dict[str, Any]:
        """
        Execute several MCP tools through one Streamable HTTP session.

        Keeping one MCP session for a dashboard refresh is substantially faster
        than opening a new connection for every Grafana tool.
        """
        ClientSession, http_client, transport = await self._session()
        results: dict[str, Any] = {}

        try:
            async with http_client:
                async with transport as streams:
                    read_stream, write_stream, _ = streams
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        for name, arguments in calls:
                            try:
                                results[name] = await session.call_tool(
                                    name,
                                    arguments or {},
                                )
                            except Exception as exc:
                                results[name] = GrafanaMCPError(
                                    f"{type(exc).__name__}: {exc}"
                                )
                        return results
        except Exception as exc:
            raise GrafanaMCPError(
                f"{type(exc).__name__}: {exc}"
            ) from exc

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        results = await self.call_tools([(name, arguments or {})])
        result = results.get(name)
        if isinstance(result, Exception):
            raise result
        return result

    async def probe(self, *, force: bool = False) -> dict[str, Any]:
        """
        Perform a real MCP handshake + tools/list call.

        Nothing is reported as healthy unless the remote MCP server
        actually responds successfully.
        """
        try:
            tools = await self.list_tools(force=force)
            return {
                "connected": True,
                "url": self.url,
                "tool_count": len(tools),
                "tools": [
                    {
                        "name": tool["name"],
                        "description": tool.get("description"),
                    }
                    for tool in tools
                ],
                "error": None,
            }
        except Exception as exc:
            return {
                "connected": False,
                "url": self.url,
                "tool_count": 0,
                "tools": [],
                "error": f"{type(exc).__name__}: {exc}",
            }

    async def inspect(self, *, force: bool = False) -> dict[str, Any]:
        """Backward-compatible alias used by older diagnostics scripts."""
        return await self.probe(force=force)
