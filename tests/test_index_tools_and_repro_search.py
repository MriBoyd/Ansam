import contextlib
import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


ROOT = Path(__file__).resolve().parents[1]

_ISOLATED_MODULES = (
    "src.hybrid_searcher",
    "hybrid_searcher",
    "src.scripts.index_tools",
    "repro_search",
)


class _DummyArray(list):
    def min(self):
        return min(self)

    def max(self):
        return max(self)

    def __sub__(self, other):
        return _DummyArray(x - other for x in self)

    def __truediv__(self, other):
        return _DummyArray(x / other for x in self)


class _DummyBM25:
    def __init__(self, corpus):
        self.corpus = corpus

    def get_scores(self, query_tokens):
        return [1.0 for _ in self.corpus]


def _install_search_third_party_stubs(monkeypatch) -> None:
    numpy_mod = types.ModuleType("numpy")
    numpy_mod.array = _DummyArray
    monkeypatch.setitem(sys.modules, "numpy", numpy_mod)

    qdrant_mod = types.ModuleType("qdrant_client")
    qdrant_models = types.ModuleType("qdrant_client.models")
    qdrant_mod.QdrantClient = MagicMock
    qdrant_models.Distance = MagicMock()
    qdrant_models.VectorParams = MagicMock
    qdrant_models.models = MagicMock()
    qdrant_models.Document = MagicMock
    qdrant_models.PointStruct = MagicMock
    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_mod)
    monkeypatch.setitem(sys.modules, "qdrant_client.models", qdrant_models)

    bm25_mod = types.ModuleType("rank_bm25")
    bm25_mod.BM25Okapi = _DummyBM25
    monkeypatch.setitem(sys.modules, "rank_bm25", bm25_mod)

    for mod_name in ("src.hybrid_searcher", "hybrid_searcher"):
        existing = sys.modules.get(mod_name)
        if existing is not None:
            monkeypatch.setattr(existing, "QdrantClient", MagicMock, raising=False)
            monkeypatch.setattr(
                existing, "Distance", qdrant_models.Distance, raising=False
            )
            monkeypatch.setattr(
                existing, "VectorParams", qdrant_models.VectorParams, raising=False
            )
            monkeypatch.setattr(existing, "models", qdrant_models.models, raising=False)
            monkeypatch.setattr(
                existing, "Document", qdrant_models.Document, raising=False
            )
            monkeypatch.setattr(
                existing, "PointStruct", qdrant_models.PointStruct, raising=False
            )
            monkeypatch.setattr(existing, "BM25Okapi", _DummyBM25, raising=False)
            monkeypatch.setattr(existing, "np", numpy_mod, raising=False)


@contextlib.contextmanager
def _isolated_search_modules():
    saved_sys_path = list(sys.path)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    saved_modules = {
        name: mod
        for name, mod in sys.modules.items()
        if name == "src"
        or name.startswith("src.")
        or name in ("hybrid_searcher", "repro_search")
    }
    src_pkg = sys.modules.get("src")
    saved_src_attrs = dict(src_pkg.__dict__) if src_pkg is not None else None
    scripts_pkg = sys.modules.get("src.scripts")
    saved_scripts_attrs = (
        dict(scripts_pkg.__dict__) if scripts_pkg is not None else None
    )

    for mod_name in _ISOLATED_MODULES:
        sys.modules.pop(mod_name, None)
    if src_pkg is not None:
        src_pkg.__dict__.pop("hybrid_searcher", None)
    if scripts_pkg is not None:
        scripts_pkg.__dict__.pop("index_tools", None)

    try:
        hybrid_searcher_mod = importlib.import_module("src.hybrid_searcher")
        index_tools_mod = importlib.import_module("src.scripts.index_tools")
        repro_search_mod = importlib.import_module("repro_search")
        yield (
            hybrid_searcher_mod.HybridToolSearcher,
            index_tools_mod,
            repro_search_mod,
        )
    finally:
        for name in [
            k
            for k in list(sys.modules)
            if k == "src"
            or k.startswith("src.")
            or k in ("hybrid_searcher", "repro_search")
        ]:
            if name not in saved_modules:
                sys.modules.pop(name, None)
        for name, mod in saved_modules.items():
            sys.modules[name] = mod
        if src_pkg is not None and saved_src_attrs is not None:
            for attr in list(src_pkg.__dict__):
                if attr not in saved_src_attrs:
                    delattr(src_pkg, attr)
            src_pkg.__dict__.update(saved_src_attrs)
        if scripts_pkg is not None and saved_scripts_attrs is not None:
            for attr in list(scripts_pkg.__dict__):
                if attr not in saved_scripts_attrs:
                    delattr(scripts_pkg, attr)
            scripts_pkg.__dict__.update(saved_scripts_attrs)
        sys.path[:] = saved_sys_path


class TestIndexToolsAndReproSearch(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _isolated_search_env(self, monkeypatch):
        _install_search_third_party_stubs(monkeypatch)
        with _isolated_search_modules() as (
            self.HybridToolSearcher,
            self.index_tools,
            self.repro_search,
        ):
            yield

    def setUp(self):
        if not hasattr(self, "HybridToolSearcher"):
            mp = self.enterContext(pytest.MonkeyPatch.context())
            _install_search_third_party_stubs(mp)
            (
                self.HybridToolSearcher,
                self.index_tools,
                self.repro_search,
            ) = self.enterContext(_isolated_search_modules())

    def test_hybrid_searcher_accepts_recreate_and_force_reindex_alias(self):
        searcher = self.HybridToolSearcher()
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
        searcher = self.HybridToolSearcher()
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

    def test_index_tools_script_passes_recreate(self):
        with patch.object(self.index_tools, "HybridToolSearcher") as mock_searcher_cls:
            mock_instance = MagicMock()
            mock_searcher_cls.return_value = mock_instance
            config_path = os.path.join(str(ROOT), "src", "mcp_servers.json")
            with patch.object(
                sys, "argv", ["index_tools.py", "--file", config_path, "--force"]
            ):
                self.index_tools.main()
            mock_instance.index.assert_called_once()
            _, kwargs = mock_instance.index.call_args
            self.assertEqual(kwargs.get("recreate"), True)

    def test_repro_search_passes_recreate_and_limit(self):
        with patch.object(self.repro_search, "HybridToolSearcher") as mock_searcher_cls:
            mock_instance = MagicMock()
            mock_instance.search.return_value = [
                {"tool_name": "fetch_url_content", "relevance_score": 0.95}
            ]
            mock_searcher_cls.return_value = mock_instance

            self.repro_search.test_capability_search()
            mock_instance.index.assert_called_once()
            _, idx_kwargs = mock_instance.index.call_args
            self.assertEqual(idx_kwargs.get("recreate"), True)

            mock_instance.search.assert_called_once_with(
                "tool that takes a URL", limit=5
            )


if __name__ == "__main__":
    unittest.main()

