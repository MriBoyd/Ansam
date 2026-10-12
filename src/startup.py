import logging
from urllib.parse import urlsplit, urlunsplit


SERVER_VERSION = "1.2.0"


def safe_endpoint(url: str) -> str:
    """Return a log-safe endpoint without credentials or query parameters."""
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    host = parsed.hostname or parsed.netloc
    if parsed.port:
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def log_startup(
    logger: logging.Logger,
    transport: str,
    host: str,
    port: int,
    qdrant_url: str,
    max_open_connections: int,
) -> None:
    """Log the active transport and bounded connection configuration."""
    address = transport
    if transport in {"sse", "http"}:
        suffix = "/sse" if transport == "sse" else ""
        address = f"{transport}://{host}:{port}{suffix}"
    logger.info(
        "Starting Ansam MCP Discovery Server v%s | transport=%s | qdrant=%s | "
        "max_open_connections=%s",
        SERVER_VERSION,
        address,
        safe_endpoint(qdrant_url),
        max_open_connections,
    )
