import asyncio
from backend.adk_app.agent import root_agent

async def main():
    mcp = root_agent.tools[-1]
    tools = await mcp.get_tools(None)

    print("MCP TOOLS:", len(tools))

    # Find the Grafana dashboard search tool.
    search_tool = next(
        (tool for tool in tools if "search_dashboards" in tool.name),
        None,
    )

    if search_tool is None:
        print("SEARCH TOOL NOT FOUND")
        return

    print("CALLING:", search_tool.name)

    result = await search_tool.run_async(
        args={"query": ""},
        tool_context=None,
    )

    print("GRAFANA MCP RESULT:")
    print(result)

asyncio.run(main())