import logging
import subprocess
import sys
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
