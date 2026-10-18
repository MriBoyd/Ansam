import importlib
import logging
import subprocess
import sys
import types
from pathlib import Path

from src.startup import SERVER_VERSION, log_startup, safe_endpoint


ROOT = Path(__file__).resolve().parents[1]


def test_version_flag_prints_version_and_exits_cleanly() -> None:
    result = subprocess.run(
        [sys.executable, "src/mcp_server_production.py", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == f"Ansam MCP Discovery Server v{SERVER_VERSION}"


def test_module_version_flag_prints_version_and_exits_cleanly() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "src.mcp_server_production", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == f"Ansam MCP Discovery Server v{SERVER_VERSION}"


def test_package_level_import_succeeds(monkeypatch) -> None:
    try:
        import fastmcp  # noqa: F401
    except ImportError:
        fastmcp_mod = types.ModuleType("fastmcp")

        class _FastMCP:
            def __init__(self, *args, **kwargs):
                pass

            def tool(self, *args, **kwargs):
                def _decorator(fn):
                    return fn
                return _decorator

            def __class_getitem__(cls, item):
                return cls

        fastmcp_mod.FastMCP = _FastMCP
        fastmcp_mod.Context = object

        server_mod = types.ModuleType("fastmcp.server")
        server_mod.create_proxy = lambda *args, **kwargs: None

        deps_mod = types.ModuleType("fastmcp.dependencies")
        deps_mod.Progress = lambda *args, **kwargs: None

        exc_mod = types.ModuleType("fastmcp.exceptions")
        exc_mod.ToolError = RuntimeError

        lifespan_mod = types.ModuleType("fastmcp.server.lifespan")
        lifespan_mod.lifespan = lambda fn: fn

        client_mod = types.ModuleType("fastmcp.client")
        transports_mod = types.ModuleType("fastmcp.client.transports")
        stdio_mod = types.ModuleType("fastmcp.client.transports.stdio")
        stdio_mod.StdioTransport = object

        for name, mod in [
            ("fastmcp", fastmcp_mod),
            ("fastmcp.server", server_mod),
            ("fastmcp.dependencies", deps_mod),
            ("fastmcp.exceptions", exc_mod),
            ("fastmcp.server.lifespan", lifespan_mod),
            ("fastmcp.client", client_mod),
            ("fastmcp.client.transports", transports_mod),
            ("fastmcp.client.transports.stdio", stdio_mod),
        ]:
            monkeypatch.setitem(sys.modules, name, mod)

    try:
        import src.hybrid_searcher  # noqa: F401
    except ImportError:
        hs_mod = types.ModuleType("src.hybrid_searcher")

        class _HybridToolSearcher:
            def __init__(self, *args, **kwargs):
                self.is_indexed = False

        hs_mod.HybridToolSearcher = _HybridToolSearcher
        monkeypatch.setitem(sys.modules, "src.hybrid_searcher", hs_mod)

    monkeypatch.delitem(sys.modules, "src.mcp_server_production", raising=False)
    mod = importlib.import_module("src.mcp_server_production")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "proxy_manager")
    assert hasattr(mod, "auth_manager")


def test_safe_endpoint_removes_credentials_and_query_parameters() -> None:
    assert (
        safe_endpoint("https://user:secret@example.com:6333/qdrant?api_key=private")
        == "https://example.com:6333/qdrant"
    )


def test_startup_log_describes_transport_without_leaking_endpoint_secrets(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="startup"):
        log_startup(
            logging.getLogger("startup"),
            "sse",
            "127.0.0.1",
            8000,
            "https://user:secret@example.com:6333/qdrant?api_key=private",
            32,
        )

    message = caplog.records[-1].getMessage()
    assert "transport=sse://127.0.0.1:8000/sse" in message
    assert "qdrant=https://example.com:6333/qdrant" in message
    assert "secret" not in message
    assert "api_key" not in message
