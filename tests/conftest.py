import importlib.util
import sys
import types
from types import SimpleNamespace
from typing import Any, List


class FallbackBM25Okapi:
    """Lightweight lexical scorer used when rank_bm25 is not installed."""

    def __init__(self, corpus: List[List[str]]) -> None:
        self.corpus = corpus

    def get_scores(self, query_tokens: List[str]) -> List[float]:
        if not query_tokens:
            return [0.0 for _ in self.corpus]
        scores: List[float] = []
        for doc in self.corpus:
            score = float(sum(doc.count(token) for token in query_tokens))
            scores.append(score)
        return scores


class _KwargStruct:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        for k, v in kwargs.items():
            setattr(self, k, v)


def ensure_search_dependencies() -> None:
    """Install complete lightweight stubs for qdrant_client and rank_bm25 when unavailable."""
    models_mod = sys.modules.get("qdrant_client.models")
    needs_qdrant_stub = (
        ("qdrant_client" not in sys.modules and importlib.util.find_spec("qdrant_client") is None)
        or (models_mod is not None and not hasattr(getattr(models_mod, "Distance", None), "COSINE"))
    )
    if needs_qdrant_stub:
        qc_mod = sys.modules.get("qdrant_client") or types.ModuleType("qdrant_client")
        if not hasattr(qc_mod, "QdrantClient"):
            setattr(qc_mod, "QdrantClient", lambda *args, **kwargs: object())

        if models_mod is None:
            models_mod = types.ModuleType("qdrant_client.models")

        models_namespace = SimpleNamespace(
            MultiVectorConfig=_KwargStruct,
            MultiVectorComparator=SimpleNamespace(MAX_SIM="max_sim"),
            HnswConfigDiff=_KwargStruct,
            SparseVectorParams=_KwargStruct,
            Modifier=SimpleNamespace(IDF="idf"),
            Prefetch=_KwargStruct,
            FusionQuery=_KwargStruct,
            Fusion=SimpleNamespace(RRF="rrf"),
            Filter=_KwargStruct,
            HasIdCondition=_KwargStruct,
        )

        setattr(models_mod, "Distance", SimpleNamespace(COSINE="Cosine"))
        setattr(models_mod, "VectorParams", _KwargStruct)
        setattr(models_mod, "models", models_namespace)
        setattr(models_mod, "Document", _KwargStruct)
        setattr(models_mod, "PointStruct", _KwargStruct)

        sys.modules["qdrant_client"] = qc_mod
        sys.modules["qdrant_client.models"] = models_mod

    bm25_mod = sys.modules.get("rank_bm25")
    needs_bm25_stub = (
        (bm25_mod is None and importlib.util.find_spec("rank_bm25") is None)
        or (bm25_mod is not None and getattr(bm25_mod, "BM25Okapi", None) is object)
    )
    if needs_bm25_stub:
        if bm25_mod is None:
            bm25_mod = types.ModuleType("rank_bm25")
        setattr(bm25_mod, "BM25Okapi", FallbackBM25Okapi)
        sys.modules["rank_bm25"] = bm25_mod

    hs_mod = sys.modules.get("src.hybrid_searcher")
    if hs_mod is not None:
        models_mod = sys.modules.get("qdrant_client.models")
        if models_mod is not None and not hasattr(getattr(hs_mod, "Distance", None), "COSINE"):
            for attr in ("Distance", "VectorParams", "models", "Document", "PointStruct"):
                setattr(hs_mod, attr, getattr(models_mod, attr))
        bm25_mod = sys.modules.get("rank_bm25")
        if bm25_mod is not None and getattr(hs_mod, "BM25Okapi", None) is object:
            setattr(hs_mod, "BM25Okapi", getattr(bm25_mod, "BM25Okapi"))


ensure_search_dependencies()
