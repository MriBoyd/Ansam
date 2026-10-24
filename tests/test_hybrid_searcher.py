import os
import re
import sys
import time
import unittest
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import ensure_search_dependencies  # noqa: E402

ensure_search_dependencies()

from src.config import Config  # noqa: E402
from src.hybrid_searcher import HybridToolSearcher  # noqa: E402


class _InMemoryQdrantClient:
    """In-memory mock for QdrantClient supporting HybridToolSearcher operations."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.collections: Dict[str, List[Any]] = {}
        self.deleted_collections: List[str] = []

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def delete_collection(self, collection_name: str) -> None:
        self.deleted_collections.append(collection_name)
        self.collections.pop(collection_name, None)

    def create_collection(self, collection_name: str, **kwargs: Any) -> None:
        self.collections[collection_name] = []

    def scroll(
        self,
        collection_name: str,
        limit: int = 1000,
        offset: Any = None,
        with_payload: bool = False,
        with_vectors: bool = False,
    ):
        points = self.collections.get(collection_name, [])
        return points[:limit], None

    def upload_points(self, collection_name: str, points: List[Any]) -> None:
        bucket = self.collections.setdefault(collection_name, [])
        existing_ids = {str(p.id) for p in bucket}
        for point in points:
            if str(point.id) not in existing_ids:
                bucket.append(point)
                existing_ids.add(str(point.id))

    def query_points(
        self,
        collection_name: str = "",
        prefetch: Any = None,
        query: Any = None,
        using: Optional[str] = None,
        limit: int = 100,
        with_payload: bool = False,
        query_filter: Any = None,
    ):
        stored = list(self.collections.get(collection_name, []))
        allowed_ids = None
        if query_filter is not None and hasattr(query_filter, "must") and query_filter.must:
            cond = query_filter.must[0]
            if hasattr(cond, "has_id"):
                allowed_ids = {str(pid) for pid in cond.has_id}

        query_text = ""
        if hasattr(query, "text"):
            query_text = str(query.text).lower()
        elif prefetch and hasattr(prefetch[0], "query") and hasattr(prefetch[0].query, "text"):
            query_text = str(prefetch[0].query.text).lower()

        query_tokens = [tok for tok in re.split(r"[^a-z0-9]+", query_text) if tok]

        scored_points = []
        for idx, pt in enumerate(stored):
            if allowed_ids is not None and str(pt.id) not in allowed_ids:
                continue
            payload = getattr(pt, "payload", {}) or {}
            haystack = f"{payload.get('name', '')} {payload.get('description', '')}".lower()
            overlap = sum(2.0 if tok in payload.get("name", "").lower() else 1.0 for tok in query_tokens if tok in haystack)
            score = overlap + (1.0 / (idx + 2))
            scored_points.append(
                SimpleNamespace(
                    id=str(pt.id),
                    score=float(score),
                    payload=payload if with_payload else None,
                )
            )

        scored_points.sort(key=lambda item: item.score, reverse=True)
        return SimpleNamespace(points=scored_points[:limit])


def _make_sample_servers() -> List[Dict[str, Any]]:
    return [
        {
            "name": "core",
            "tools": [
                {
                    "name": "create_github_issue",
                    "description": "Create a new issue in a GitHub repository",
                    "parameters": {
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "Issue title"},
                        "body": {"type": "string", "description": "Issue description"},
                    },
                    "required": ["repo", "title"],
                },
                {
                    "name": "send_slack_message",
                    "description": "Send a message to a Slack channel",
                    "parameters": {
                        "channel": {"type": "string", "description": "Channel ID"},
                        "text": {"type": "string", "description": "Message text"},
                    },
                    "required": ["channel", "text"],
                },
                {
                    "name": "execute_sql_query",
                    "description": "Execute a SQL query on the database",
                    "parameters": {
                        "query": {"type": "string", "description": "SQL query"},
                        "database": {"type": "string", "description": "Database name"},
                    },
                    "required": ["query"],
                },
            ],
        }
    ]


class TestHybridToolSearcher(unittest.TestCase):
    """Unit tests for the three-stage Qdrant HybridToolSearcher."""

    def setUp(self) -> None:
        self.sample_tools = _make_sample_servers()
        with patch("src.hybrid_searcher.QdrantClient", side_effect=_InMemoryQdrantClient):
            self.searcher = HybridToolSearcher()

    def test_initialization(self) -> None:
        """Searcher initializes client, model identifiers, and empty state."""
        self.assertIsNotNone(self.searcher.client)
        self.assertEqual(self.searcher.collection_name, "tool-search")
        self.assertEqual(self.searcher.dense_model, "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(self.searcher.sparse_model, "prithivida/Splade_PP_en_v1")
        self.assertEqual(self.searcher.rerank_model, "colbert-ir/colbertv2.0")
        self.assertEqual(self.searcher.tools, [])
        self.assertIsNone(self.searcher.bm25)
        self.assertFalse(self.searcher.is_indexed)

    def test_tool_to_text_standard_and_input_schema(self) -> None:
        """_tool_to_text formats both parameters and inputSchema tool definitions."""
        tool = self.sample_tools[0]["tools"][0]
        text = self.searcher._tool_to_text(tool)

        self.assertIn("tool: create_github_issue", text)
        self.assertIn("description: create a new issue in a github repository", text)
        self.assertIn("repo: repository name", text)
        self.assertIn("required parameters: repo, title", text)

        schema_tool = {
            "name": "list_pull_requests",
            "server": "github",
            "description": "List pull requests",
            "inputSchema": {
                "properties": {
                    "state": {"type": "string", "description": "PR state filter"},
                },
                "required": ["state"],
            },
        }
        schema_text = self.searcher._tool_to_text(schema_tool)
        self.assertIn("tool: list_pull_requests", schema_text)
        self.assertIn("server: github", schema_text)
        self.assertIn("state: pr state filter", schema_text)
        self.assertIn("required parameters: state", schema_text)

    def test_tokenize_handles_camel_case_and_symbols(self) -> None:
        """_tokenize splits camelCase and non-alphanumeric separators."""
        tokens = self.searcher._tokenize("createGithubIssue_v2/test")
        self.assertEqual(tokens, ["create", "github", "issue", "v2", "test"])
        self.assertEqual(self.searcher._tokenize(""), [])

    def test_index_tools_and_recreate(self) -> None:
        """index(tools, recreate=...) populates BM25, Qdrant points, and is_indexed."""
        self.searcher.index(self.sample_tools)

        self.assertTrue(self.searcher.is_indexed)
        self.assertIsNotNone(self.searcher.bm25)
        self.assertEqual(len(self.searcher.tools), 3)
        self.assertEqual(len(self.searcher.client.collections["tool-search"]), 3)

        # Re-indexing with recreate=True deletes and recreates the collection
        self.searcher.index({"servers": self.sample_tools}, recreate=True)
        self.assertIn("tool-search", self.searcher.client.deleted_collections)
        self.assertEqual(len(self.searcher.tools), 3)

    def test_search_pipeline_and_limit(self) -> None:
        """search(query, limit=...) returns ranked tool dictionaries."""
        self.searcher.index(self.sample_tools)

        queries = [
            "create a github issue",
            "send message to slack",
            "run sql query",
        ]
        for query in queries:
            results = self.searcher.search(query, limit=2)
            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)
            self.assertLessEqual(len(results), 2)
            top = results[0]
            self.assertIn("tool_name", top)
            self.assertIn("tool_description", top)
            self.assertIn("tool_schema", top)
            self.assertIn("relevance_score", top)
            self.assertIsInstance(top["relevance_score"], float)

    def test_search_without_indexing_returns_empty_list(self) -> None:
        """Calling search before index returns an empty list rather than raising."""
        results = self.searcher.search("test query", limit=5)
        self.assertEqual(results, [])

    def test_search_empty_tools(self) -> None:
        """Indexing an empty tool list leaves searcher unindexed and returns []."""
        self.searcher.index([])
        self.assertFalse(self.searcher.is_indexed)
        self.assertEqual(self.searcher.search("test query", limit=5), [])

    def test_search_uses_cache(self) -> None:
        """Repeated identical search calls return cached results."""
        self.searcher.index(self.sample_tools)
        first = self.searcher.search("create github issue", limit=1)
        second = self.searcher.search("create github issue", limit=1)
        self.assertEqual(first, second)


class TestHybridSearcherConfig(unittest.TestCase):
    """Test configuration settings on Config."""

    def test_config_values(self) -> None:
        self.assertTrue(hasattr(Config, "BM25_CANDIDATES"))
        self.assertTrue(hasattr(Config, "DENSE_CANDIDATES"))
        self.assertTrue(hasattr(Config, "FUSION_CANDIDATES"))
        self.assertTrue(hasattr(Config, "FINAL_RESULTS"))
        self.assertTrue(hasattr(Config, "BM25_WEIGHT"))
        self.assertTrue(hasattr(Config, "DENSE_WEIGHT"))
        self.assertTrue(hasattr(Config, "QDRANT_URL"))
        self.assertTrue(hasattr(Config, "QDRANT_COLLECTION"))

    def test_fusion_weights(self) -> None:
        total = Config.BM25_WEIGHT + Config.DENSE_WEIGHT
        self.assertAlmostEqual(total, 1.0, places=5)


def create_benchmark_searcher(num_tools: int = 100) -> Tuple[HybridToolSearcher, List[Dict[str, Any]]]:
    """Create an in-memory HybridToolSearcher and synthetic dataset for performance benchmarks."""
    with patch("src.hybrid_searcher.QdrantClient", side_effect=_InMemoryQdrantClient):
        searcher = HybridToolSearcher()

    tools = []
    for i in range(num_tools):
        tools.append(
            {
                "name": f"tool_{i}",
                "description": f"Description for tool {i} data analysis "
                + " ".join(f"keyword{j}" for j in range(5)),
                "parameters": {
                    f"param_{j}": {"type": "string", "description": f"Parameter {j}"}
                    for j in range(3)
                },
                "required": ["param_0"],
            }
        )
    large_tools = [{"name": "benchmark_server", "tools": tools}]
    return searcher, large_tools


class TestPerformance(unittest.TestCase):
    """Performance tests for indexing and searching 100 tools."""

    def setUp(self) -> None:
        self.searcher, self.large_tools = create_benchmark_searcher()

    def test_indexing_performance(self) -> None:
        start = time.time()
        self.searcher.index(self.large_tools, recreate=True)
        duration = time.time() - start
        self.assertTrue(self.searcher.is_indexed)
        self.assertEqual(len(self.searcher.tools), 100)
        self.assertLess(duration, 60)

    def test_search_performance(self) -> None:
        self.searcher.index(self.large_tools, recreate=True)
        start = time.time()
        results = self.searcher.search("test query", limit=5)
        duration = time.time() - start
        self.assertEqual(len(results), 5)
        self.assertLess(duration, 5)


class TestIntegration(unittest.TestCase):
    """Integration-style tests over indexed tool definitions."""

    def setUp(self) -> None:
        with patch("src.hybrid_searcher.QdrantClient", side_effect=_InMemoryQdrantClient):
            self.searcher = HybridToolSearcher()
        self.tools = _make_sample_servers()
        self.searcher.index(self.tools, recreate=True)

    def test_semantic_search_github(self) -> None:
        results = self.searcher.search("Create a new issue in a GitHub repository", limit=3)
        found_github = any("github" in r["tool_name"].lower() for r in results)
        self.assertTrue(found_github)

    def test_exact_match_priority(self) -> None:
        results = self.searcher.search("create_github_issue", limit=3)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["tool_name"], "create_github_issue")

    def test_query_diversity(self) -> None:
        for query in ["create issue", "send slack", "sql query", "database"]:
            results = self.searcher.search(query, limit=2)
            self.assertIsInstance(results, list)
            self.assertGreater(len(results), 0)


class TestEdgeCases(unittest.TestCase):
    """Edge cases and input resilience tests."""

    def setUp(self) -> None:
        self.sample_tools = _make_sample_servers()
        with patch("src.hybrid_searcher.QdrantClient", side_effect=_InMemoryQdrantClient):
            self.searcher = HybridToolSearcher()

    def test_empty_query(self) -> None:
        self.searcher.index(self.sample_tools)
        results = self.searcher.search("", limit=3)
        self.assertIsInstance(results, list)

    def test_special_characters_in_query(self) -> None:
        self.searcher.index(self.sample_tools)
        for query in ["create@#$%", "send/message", "sql_query()", "repo:owner/name"]:
            results = self.searcher.search(query, limit=2)
            self.assertIsInstance(results, list)

    def test_unicode_query(self) -> None:
        self.searcher.index(self.sample_tools)
        for query in ["创建问题", "создать задачу", "créer un problème"]:
            results = self.searcher.search(query, limit=2)
            self.assertIsInstance(results, list)

    def test_very_long_query(self) -> None:
        self.searcher.index(self.sample_tools)
        results = self.searcher.search("test " * 1000, limit=2)
        self.assertIsInstance(results, list)


if __name__ == "__main__":
    unittest.main()