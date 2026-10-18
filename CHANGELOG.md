# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Automated GitHub Actions CI workflow for pull requests and main branch validation.
- Automatic `.env` file configuration loading with `python-dotenv`.
- Connection retry logic with exponential backoff on startup for Qdrant.

## [1.2.0] - 2026-10-18

### Added
- `--version` CLI flag and startup configuration banner summarizing active configuration, transport mode, and connection pool capacity ([#1](https://github.com/MriBoyd/Ansam/issues/1), [PR #5](https://github.com/MriBoyd/Ansam/pull/5)).
- Standalone runnable client examples for stdio (`examples/stdio_client.py`) and SSE (`examples/sse_client.py`) with comprehensive documentation ([#4](https://github.com/MriBoyd/Ansam/issues/4), [PR #6](https://github.com/MriBoyd/Ansam/pull/6)).
- Contributing guide (`CONTRIBUTING.md`), issue templates for bug reports and beginner tasks, and pull request template.
- Integration tests for `mcp_crawler` and extended concurrency unit tests for rate limiting.

### Changed
- Renamed repository to **Ansam** (`MriBoyd/Ansam`) with updated documentation and clone instructions.
- Renamed FastMCP server instance to `Ansam`.
- Switched default search retrieval pipeline to three-stage Qdrant hybrid retrieval: Dense embeddings (`all-MiniLM-L6-v2`), Sparse vectors (`Splade_PP_en_v1`), and ColBERT late-interaction reranking (`colbertv2.0`).

### Fixed
- Fixed lock-holding sleep in `TokenBucketRateLimiter.acquire()` that blocked concurrent callers, and added input guards to prevent deadlocks when requested tokens exceed capacity ([#11](https://github.com/MriBoyd/Ansam/issues/11), [PR #15](https://github.com/MriBoyd/Ansam/pull/15)).
- Fixed invalid path calculation in `src/scripts/mcp_crawler.py` that caused `FileNotFoundError` ([#10](https://github.com/MriBoyd/Ansam/issues/10), [PR #14](https://github.com/MriBoyd/Ansam/pull/14)).
- Sanitized sensitive credentials from startup logs to prevent secret leakage ([PR #5](https://github.com/MriBoyd/Ansam/pull/5)).

## [1.1.0] - 2026-04-29

### Added
- Dynamic proxy pooling via `DynamicProxyManager` with `ConcurrentLRUCache` to efficiently manage connections to up to 1000+ downstream MCP servers.
- Built-in `CircuitBreaker` and `CircuitBreakerManager` to prevent cascading failures from unresponsive downstream servers.
- `RateLimiterManager` supporting global and per-server token-bucket rate limiting.
- `AuthManager` with OAuth2 code exchange, token refresh, and PKCE (S256) support.
- Universal `MCPRegistryManager` supporting tool extraction from `stdio`, `sse`, and `http` MCP server transports.
- Incremental Qdrant indexing supporting both list and dictionary server configurations.

### Changed
- Transitioned from local neural reranking to native in-database ColBERT scoring via Qdrant multi-vector support.

## [1.0.0] - 2026-04-14

### Added
- Initial release of the MCP Tool Discovery Server.
- Offline hybrid tool search with BM25 and dense embeddings.
- Basic proxy execution and stdio transport support.
- Tool indexing scripts and sample tool registries.
