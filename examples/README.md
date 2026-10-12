# Ansam examples

Small, standalone clients that show how to talk to the Ansam MCP Discovery
Server. Each script is self-contained and comments every step, so you can copy
it into your own project.

| Script | Transport | Server must be running? |
| --- | --- | --- |
| [`stdio_client.py`](stdio_client.py) | stdio | No — the script launches it |
| [`sse_client.py`](sse_client.py) | SSE | Yes — start it first |

Both scripts call the server's `search_tools` tool, which runs the hybrid
retrieval pipeline and returns the most relevant tools for a natural-language
query.

## Prerequisites

- Python 3.10+
- The project dependencies installed from the repository root:

  ```bash
  pip install -r requirements.txt
  pip install -e ".[dev]"
  ```

- A running **Qdrant** instance, because `search_tools` searches a vector
  index. See the "Running Qdrant" section of the root
  [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the Docker command.

The index itself is populated by the ingestion script, if you have not done
that yet:

```bash
python src/scripts/index_tools.py --file src/mcp_servers.json
```

## Run the stdio example

This script starts `src/mcp_server_production.py` as a subprocess and speaks
the stdio transport to it, so there is nothing to start by hand:

```bash
python examples/stdio_client.py "find a tool that fetches the weather"
```

The query is optional; without one the script uses a built-in default.

## Run the SSE example

The SSE client connects to an already-running server, so start the server
first in its own terminal:

```bash
python src/mcp_server_production.py --sse --port 8000
```

Then, in a second terminal, run the client:

```bash
python examples/sse_client.py "find a tool that fetches the weather"
```

The server exposes its SSE endpoint at `http://localhost:8000/sse`. To point
the client at a different endpoint, pass the URL as the first argument:

```bash
python examples/sse_client.py http://localhost:8000/sse "my query"
```

## What the output looks like

Both scripts print the tools the server advertises, then the text returned by
`search_tools` for your query:

```text
Connected. 1 tool(s) available:
  - search_tools

Searching for: 'find a tool that fetches the weather'
<input follows the server's configured result format>
```

If the client cannot reach the server over SSE, confirm the server is running
and that the port matches the one you passed to `--port`.