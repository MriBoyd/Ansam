"""Minimal MCP client that talks to Ansam over the stdio transport.

Run the discovery server as a subprocess and call its `search_tools` tool.
This is the transport you get when you start the server with no flags:

    python src/mcp_server_production.py

Prerequisites (see examples/README.md):
    pip install -r requirements.txt
    pip install -e ".[dev]"

Usage:
    python examples/stdio_client.py "find a tool that fetches the weather"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Absolute path to the server entry point, so the example works no matter
# which directory it is launched from.
SERVER_SCRIPT = Path(__file__).resolve().parents[1] / "src" / "mcp_server_production.py"

# Adjust this if you want to try a different query.
DEFAULT_QUERY = "I need a tool to fetch weather data and send an email"


async def main(query: str) -> None:
    # StdioServerParameters tells the client how to launch the server.
    # `cwd` is set to the repository root so the server's relative imports
    # and its `mcp_servers.json` lookup resolve the same way as a manual run.
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
        cwd=str(SERVER_SCRIPT.parent.parent),
    )

    # stdio_client spawns the server and yields the read/write streams that
    # ClientSession wraps into a request/response channel.
    # ClientSession turns the read/write streams into a request/response
    # channel. The two context managers are opened together.
    async with (
        stdio_client(server_params) as (read, write),
        ClientSession(read, write) as session,
    ):
        # The handshake must happen before any tool call.
        await session.initialize()

        # List the tools the server advertises.
        tools = await session.list_tools()
        print(f"Connected. {len(tools.tools)} tool(s) available:")
        for tool in tools.tools:
            print(f"  - {tool.name}")

        # Call the hybrid-search tool with a natural-language query.
        # `search_tools` returns a human-readable string of matches.
        print(f"\nSearching for: {query!r}")
        result = await session.call_tool("search_tools", {"query": query})

        # Tool results arrive as a list of content blocks; print the text.
        for block in result.content:
            text = getattr(block, "text", None)
            if text is not None:
                print(text)


if __name__ == "__main__":
    user_query = " ".join(sys.argv[1:]) or DEFAULT_QUERY
    asyncio.run(main(user_query))
