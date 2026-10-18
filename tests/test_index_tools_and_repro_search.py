import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Provide lightweight stubs if qdrant_client / rank_bm25 are not installed in the test environment
if "qdrant_client" not in sys.modules:
    qdrant_mod = types.ModuleType("qdrant_client")
    qdrant_models = types.ModuleType("qdrant_client.models")
    qdrant_mod.QdrantClient = MagicMock
    qdrant_models.Distance = MagicMock()
    qdrant_models.VectorParams = MagicMock
    qdrant_models.models = MagicMock()
    qdrant_models.Document = MagicMock
    qdrant_models.PointStruct = MagicMock
    sys.modules["qdrant_client"] = qdrant_mod
    sys.modules["qdrant_client.models"] = qdrant_models

if "rank_bm25" not in sys.modules:
    bm25_mod = types.ModuleType("rank_bm25")

    class _DummyBM25:
        def __init__(self, corpus):
            self.corpus = corpus

        def get_scores(self, query_tokens):
            return [1.0 for _ in self.corpus]

    bm25_mod.BM25Okapi = _DummyBM25
    sys.modules["rank_bm25"] = bm25_mod

from src.hybrid_searcher import HybridToolSearcher
from src.scripts import index_tools
import repro_search


class TestIndexToolsAndReproSearch(unittest.TestCase):
    def test_hybrid_searcher_accepts_recreate_and_force_reindex_alias(self):
        searcher = HybridToolSearcher()
        searcher.client = MagicMock()
        searcher.client.collection_exists.return_value = True
        searcher.client.scroll.return_value = ([], None)

        tools = [
            {
                "name": "fetch_url_content",
                "description": "Fetch the content of a given URL",
                "parameters": {"url": {"type": "string", "description": "URL"}},
                "required": ["url"],
            }
        ]
        searcher.index(tools, recreate=True)
        self.assertTrue(searcher.is_indexed)
        self.assertEqual(len(searcher.tools), 1)
        searcher.client.delete_collection.assert_called_with(searcher.collection_name)

        searcher.client.delete_collection.reset_mock()
        searcher.index(tools, force_reindex=True)
        searcher.client.delete_collection.assert_called_with(searcher.collection_name)

    def test_hybrid_searcher_accepts_limit_and_top_k_alias(self):
        searcher = HybridToolSearcher()
        searcher.client = MagicMock()
        searcher.is_indexed = True
        searcher.tools = [
            {"name": "tool_a", "description": "A"},
            {"name": "tool_b", "description": "B"},
        ]

        p1 = MagicMock()
        p1.id = searcher._str_to_uuid("tool_a")
        p1.score = 0.9
        p1.payload = searcher.tools[0]
        p2 = MagicMock()
        p2.id = searcher._str_to_uuid("tool_b")
        p2.score = 0.5
        p2.payload = searcher.tools[1]

        resp = MagicMock()
        resp.points = [p1, p2]
        searcher.client.query_points.return_value = resp

        res_limit = searcher.search("query a", limit=1)
        self.assertEqual(len(res_limit), 1)

        res_top_k = searcher.search("query b", top_k=1)
        self.assertEqual(len(res_top_k), 1)

    @patch("src.scripts.index_tools.HybridToolSearcher")
    def test_index_tools_script_passes_recreate(self, mock_searcher_cls):
        mock_instance = MagicMock()
        mock_searcher_cls.return_value = mock_instance
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "src",
            "mcp_servers.json",
        )
        with patch.object(sys, "argv", ["index_tools.py", "--file", config_path, "--force"]):
            index_tools.main()
        mock_instance.index.assert_called_once()
        _, kwargs = mock_instance.index.call_args
        self.assertEqual(kwargs.get("recreate"), True)

    @patch("repro_search.HybridToolSearcher")
    def test_repro_search_passes_recreate_and_limit(self, mock_searcher_cls):
        mock_instance = MagicMock()
        mock_instance.search.return_value = [
            {"tool_name": "fetch_url_content", "relevance_score": 0.95}
        ]
        mock_searcher_cls.return_value = mock_instance

        repro_search.test_capability_search()
        mock_instance.index.assert_called_once()
        _, idx_kwargs = mock_instance.index.call_args
        self.assertEqual(idx_kwargs.get("recreate"), True)

        mock_instance.search.assert_called_once_with("tool that takes a URL", limit=5)


if __name__ == "__main__":
    unittest.main()
