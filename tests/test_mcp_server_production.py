import contextlib
import importlib
import logging
import subprocess
import sys
import types
from pathlib import Path

import pytest

from src.startup import SERVER_VERSION, log_startup, safe_endpoint


ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def _isolated_src_modules():
    saved_src_modules = {
        name: mod
        for name, mod in sys.modules.items()
        if name == "src" or name.startswith("src.")
    }
    src_pkg = sys.modules.get("src")
    saved_src_attrs = dict(src_pkg.__dict__) if src_pkg is not None else None

    for name in ("src.auth_manager", "src.hybrid_searcher", "src.mcp_server_production"):
        sys.modules.pop(name, None)
    if src_pkg is not None:
        for attr in ("auth_manager", "hybrid_searcher", "mcp_server_production"):
            src_pkg.__dict__.pop(attr, None)

    try:
        yield
    finally:
        for name in [
            k for k in list(sys.modules) if k == "src" or k.startswith("src.")
        ]:
            if name not in saved_src_modules:
                sys.modules.pop(name, None)
        for name, mod in saved_src_modules.items():
            sys.modules[name] = mod
        if src_pkg is not None and saved_src_attrs is not None:
            for attr in list(src_pkg.__dict__):
                if attr not in saved_src_attrs:
                    delattr(src_pkg, attr)
            src_pkg.__dict__.update(saved_src_attrs)


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
        import httpx  # noqa: F401
    except ImportError:
        monkeypatch.setitem(sys.modules, "httpx", types.ModuleType("httpx"))

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
    before_src_modules = {
        k: v for k, v in sys.modules.items() if k == "src" or k.startswith("src.")
    }

    with _isolated_src_modules():
        mod = importlib.import_module("src.mcp_server_production")
        assert hasattr(mod, "mcp")
        assert hasattr(mod, "proxy_manager")
        assert hasattr(mod, "auth_manager")
        assert mod.HybridToolSearcher.__module__ == "src.hybrid_searcher"

    after_src_modules = {
        k: v for k, v in sys.modules.items() if k == "src" or k.startswith("src.")
    }
    assert after_src_modules == before_src_modules


def test_package_level_import_propagates_third_party_import_error(monkeypatch) -> None:
    _install_fastmcp_stub(monkeypatch)
    _install_search_third_party_stubs(monkeypatch)
    monkeypatch.setitem(sys.modules, "qdrant_client", None)
    monkeypatch.delitem(sys.modules, "qdrant_client.models", raising=False)
    before_src_modules = {
        k: v for k, v in sys.modules.items() if k == "src" or k.startswith("src.")
    }

    with _isolated_src_modules():
        with pytest.raises(ModuleNotFoundError) as exc_info:
            importlib.import_module("src.mcp_server_production")

        assert exc_info.value.name == "qdrant_client"

    after_src_modules = {
        k: v for k, v in sys.modules.items() if k == "src" or k.startswith("src.")
    }
    assert after_src_modules == before_src_modules


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
