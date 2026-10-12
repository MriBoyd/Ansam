"""Minimal MCP client that talks to Ansam over the SSE transport.

Start the server with the SSE transport first, in its own terminal:

    python src/mcp_server_production.py --sse --port 8000

The FastMCP server exposes its SSE endpoint at `/sse` on that port, so the
client below connects to http://localhost:8000/sse.

Prerequisites (see examples/README.md):
    pip install -r requirements.txt
    pip install -e ".[dev]"

Usage:
    python examples/sse_client.py "find a tool that fetches the weather"
"""

from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession
from mcp.client.sse import sse_client

# Default endpoint matches `--sse --port 8000` from the run command above.
SERVER_URL = "http://localhost:8000/sse"

# Adjust this if you want to try a different query.
DEFAULT_QUERY = "I need a tool to fetch weather data and send an email"


async def main(url: str, query: str) -> None:
    # sse_client opens the long-lived SSE stream and yields the read/write
    # streams that ClientSession turns into a request/response channel.
    # Unlike the stdio example, nothing is spawned here: the server must
    # already be running and reachable at `url`.
    # ClientSession turns the read/write streams into a request/response
    # channel. The two context managers are opened together.
    async with (
        sse_client(url) as (read, write),
        ClientSession(read, write) as session,
    ):
        # The handshake must happen before any tool call.
        await session.initialize()

        # List the tools the server advertises.
        tools = await session.list_tools()
        print(f"Connected to {url}. {len(tools.tools)} tool(s) available:")
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
    args = sys.argv[1:]
    # Optional first argument overrides the SSE endpoint.
    server_url = args[0] if args and args[0].startswith("http") else SERVER_URL
    rest = args[1:] if args and args[0].startswith("http") else args
    user_query = " ".join(rest) or DEFAULT_QUERY
    asyncio.run(main(server_url, user_query))
