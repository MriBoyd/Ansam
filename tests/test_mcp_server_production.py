import importlib
import logging
import subprocess
import sys
import types
from pathlib import Path

import pytest

from src.startup import SERVER_VERSION, log_startup, safe_endpoint


ROOT = Path(__file__).resolve().parents[1]


def _install_fastmcp_stub(monkeypatch) -> None:
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


def _install_search_third_party_stubs(monkeypatch) -> None:
    try:
        import numpy  # noqa: F401
    except ImportError:
        monkeypatch.setitem(sys.modules, "numpy", types.ModuleType("numpy"))

    try:
        import qdrant_client  # noqa: F401
    except ImportError:
        qc_mod = types.ModuleType("qdrant_client")
        qc_mod.QdrantClient = lambda *args, **kwargs: object()
        models_mod = types.ModuleType("qdrant_client.models")
        for attr in ("Distance", "VectorParams", "models", "Document", "PointStruct"):
            setattr(models_mod, attr, object)
        monkeypatch.setitem(sys.modules, "qdrant_client", qc_mod)
        monkeypatch.setitem(sys.modules, "qdrant_client.models", models_mod)

    try:
        import rank_bm25  # noqa: F401
    except ImportError:
        bm25_mod = types.ModuleType("rank_bm25")
        bm25_mod.BM25Okapi = object
        monkeypatch.setitem(sys.modules, "rank_bm25", bm25_mod)


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
    _install_fastmcp_stub(monkeypatch)
    _install_search_third_party_stubs(monkeypatch)
    monkeypatch.delitem(sys.modules, "src.hybrid_searcher", raising=False)
    monkeypatch.delitem(sys.modules, "src.mcp_server_production", raising=False)

    mod = importlib.import_module("src.mcp_server_production")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "proxy_manager")
    assert hasattr(mod, "auth_manager")
    assert mod.HybridToolSearcher.__module__ == "src.hybrid_searcher"


def test_package_level_import_propagates_third_party_import_error(monkeypatch) -> None:
    _install_fastmcp_stub(monkeypatch)
    monkeypatch.setitem(sys.modules, "qdrant_client", None)
    monkeypatch.delitem(sys.modules, "src.hybrid_searcher", raising=False)
    monkeypatch.delitem(sys.modules, "src.mcp_server_production", raising=False)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        importlib.import_module("src.mcp_server_production")

    assert exc_info.value.name == "qdrant_client"


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
