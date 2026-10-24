# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Automated GitHub Actions CI workflow for pull requests and main branch validation ([#8](https://github.com/MriBoyd/Ansam/issues/8), [PR #22](https://github.com/MriBoyd/Ansam/pull/22)).
- Automatic `.env` file configuration loading with `python-dotenv` ([#2](https://github.com/MriBoyd/Ansam/issues/2), [PR #19](https://github.com/MriBoyd/Ansam/pull/19)).
- Connection retry logic with exponential backoff on startup for Qdrant ([#3](https://github.com/MriBoyd/Ansam/issues/3), [PR #21](https://github.com/MriBoyd/Ansam/pull/21)).
- Backwards-compatible `force_reindex` and `top_k` parameter aliases in `HybridToolSearcher` ([#13](https://github.com/MriBoyd/Ansam/issues/13), [PR #17](https://github.com/MriBoyd/Ansam/pull/17)).

### Fixed
- Cleaned up obsolete test modules (`test_code_embedder.py` and `test_local_reranker.py`) from the pre-ColBERT architecture and fixed pytest collection errors ([#7](https://github.com/MriBoyd/Ansam/issues/7), [PR #20](https://github.com/MriBoyd/Ansam/pull/20)).
- Consolidated mock search dependency stubs in `tests/conftest.py` (`Distance.COSINE`, `_KwargStruct`, and `FallbackBM25Okapi`) to eliminate execution-order mock collisions and missing attribute errors ([#7](https://github.com/MriBoyd/Ansam/issues/7), [PR #20](https://github.com/MriBoyd/Ansam/pull/20)).
- Updated `tests/test_score_normalization.py` to validate `HybridToolSearcher._min_max_scale()` across multi-value, single-value, empty, identical, and mixed-sign score sets ([#7](https://github.com/MriBoyd/Ansam/issues/7), [PR #20](https://github.com/MriBoyd/Ansam/pull/20)).
- Updated `tests/test_hybrid_searcher.py` and `tests/test_performance.py` to match the current `HybridToolSearcher` API and extracted `create_benchmark_searcher()` to prevent duplicate test collection and class name collisions ([#7](https://github.com/MriBoyd/Ansam/issues/7), [PR #20](https://github.com/MriBoyd/Ansam/pull/20)).
- Fixed `TypeError` in `src/scripts/index_tools.py` and `repro_search.py` by aligning `recreate` and `limit` parameter names with `HybridToolSearcher` ([#13](https://github.com/MriBoyd/Ansam/issues/13), [PR #17](https://github.com/MriBoyd/Ansam/pull/17)).
- Supported flat tool list ingestion in `HybridToolSearcher.index()` alongside server-grouped structures ([#13](https://github.com/MriBoyd/Ansam/issues/13), [PR #17](https://github.com/MriBoyd/Ansam/pull/17)).
- `HybridToolSearcher` now defaults `qdrant_url` and `collection_name` to `Config.QDRANT_URL` and `Config.QDRANT_COLLECTION` instead of hardcoded `http://0.0.0.0:6333` / `tool-search`, so `.env` settings apply to both `src/scripts/index_tools.py` indexing and `src/mcp_server_production.py` search ([#25](https://github.com/MriBoyd/Ansam/issues/25)).

### Security
- Added `tokens.json` to `.gitignore` to prevent committing OAuth credentials to version control ([#12](https://github.com/MriBoyd/Ansam/issues/12), [PR #18](https://github.com/MriBoyd/Ansam/pull/18)).
- Enforced restrictive `0600` (`-rw-------`) file permissions on token creation and updates in `AuthManager._save_tokens()` ([#12](https://github.com/MriBoyd/Ansam/issues/12), [PR #18](https://github.com/MriBoyd/Ansam/pull/18)).

## [1.2.0] - 2026-10-18

### Added
- `--version` CLI flag and startup configuration banner summarizing active configuration, transport mode, and connection pool capacity ([#1](https://github.com/MriBoyd/Ansam/issues/1), [PR #5](https://github.com/MriBoyd/Ansam/pull/5)).
- Standalone runnable client examples for stdio (`examples/stdio_client.py`) and SSE (`examples/sse_client.py`) with comprehensive documentation ([#4](https://github.com/MriBoyd/Ansam/issues/4), [PR #6](https://github.com/MriBoyd/Ansam/pull/6)).
- Contributing guide (`CONTRIBUTING.md`), issue templates for bug reports and beginner tasks, and pull request template.
- Integration tests for `mcp_crawler` and extended concurrency unit tests for rate limiting.
- Unit tests verifying package-level importability and module `--version` execution with isolated submodule state management ([PR #16](https://github.com/MriBoyd/Ansam/pull/16)).

### Changed
- Renamed repository to **Ansam** (`MriBoyd/Ansam`) with updated documentation and clone instructions.
- Renamed FastMCP server instance to `Ansam`.
- Switched default search retrieval pipeline to three-stage Qdrant hybrid retrieval: Dense embeddings (`all-MiniLM-L6-v2`), Sparse vectors (`Splade_PP_en_v1`), and ColBERT late-interaction reranking (`colbertv2.0`).

### Fixed
- Fixed `ModuleNotFoundError` when importing `src.mcp_server_production` or executing as a module (`python -m src.mcp_server_production`) by resolving package-qualified imports with scoped fallback to bare module imports ([#9](https://github.com/MriBoyd/Ansam/issues/9), [PR #16](https://github.com/MriBoyd/Ansam/pull/16)).
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
