import importlib.util
import logging
import sys
import types
import unittest
from typing import Any
from unittest.mock import MagicMock, patch


def _ensure_search_dependencies() -> None:
    if "qdrant_client" not in sys.modules and importlib.util.find_spec("qdrant_client") is None:
        qc_mod = types.ModuleType("qdrant_client")
        setattr(qc_mod, "QdrantClient", lambda *args, **kwargs: object())
        models_mod = types.ModuleType("qdrant_client.models")
        for attr in ("Distance", "VectorParams", "models", "Document", "PointStruct"):
            setattr(models_mod, attr, object)
        sys.modules["qdrant_client"] = qc_mod
        sys.modules["qdrant_client.models"] = models_mod

    if "rank_bm25" not in sys.modules and importlib.util.find_spec("rank_bm25") is None:
        bm25_mod = types.ModuleType("rank_bm25")
        setattr(bm25_mod, "BM25Okapi", object)
        sys.modules["rank_bm25"] = bm25_mod


_ensure_search_dependencies()

from src.config import Config  # noqa: E402
from src.hybrid_searcher import HybridToolSearcher  # noqa: E402


class TestQdrantStartupRetry(unittest.TestCase):
    """Unit tests for Qdrant startup connection retry with exponential backoff (#3)."""

    def test_connects_immediately_when_qdrant_is_ready(self) -> None:
        mock_client = MagicMock()
        with (
            patch("src.hybrid_searcher.QdrantClient", return_value=mock_client) as mock_cls,
            patch("src.hybrid_searcher.time.sleep") as mock_sleep,
        ):
            searcher = HybridToolSearcher(qdrant_url="http://localhost:6333")

        self.assertIs(searcher.client, mock_client)
        mock_cls.assert_called_once_with(url="http://localhost:6333")
        mock_client.get_collections.assert_called_once_with()
        mock_sleep.assert_not_called()

    def test_retries_with_exponential_backoff_on_client_creation_failure(self) -> None:
        mock_client = MagicMock()
        side_effects: list[Any] = [
            ConnectionError("Connection refused 1"),
            ConnectionError("Connection refused 2"),
            mock_client,
        ]
        with (
            patch("src.hybrid_searcher.QdrantClient", side_effect=side_effects) as mock_cls,
            patch("src.hybrid_searcher.time.sleep") as mock_sleep,
            self.assertLogs(level=logging.WARNING) as captured,
        ):
            searcher = HybridToolSearcher(
                qdrant_url="http://localhost:6333",
                max_retries=5,
                retry_delay=1.0,
                backoff_factor=2.0,
                max_retry_delay=16.0,
            )

        self.assertIs(searcher.client, mock_client)
        self.assertEqual(mock_cls.call_count, 3)
        self.assertEqual([call.args[0] for call in mock_sleep.call_args_list], [1.0, 2.0])
        joined_logs = "\n".join(captured.output)
        self.assertIn("Waiting for Qdrant to be ready (attempt 2/5)...", joined_logs)
        self.assertIn("Waiting for Qdrant to be ready (attempt 3/5)...", joined_logs)

    def test_retries_when_readiness_probe_fails_then_succeeds(self) -> None:
        mock_client = MagicMock()
        mock_client.get_collections.side_effect = [
            OSError("Qdrant starting"),
            OSError("Still warming up"),
            OSError("Almost ready"),
            MagicMock(),
        ]
        with (
            patch("src.hybrid_searcher.QdrantClient", return_value=mock_client),
            patch("src.hybrid_searcher.time.sleep") as mock_sleep,
            self.assertLogs(level=logging.WARNING) as captured,
        ):
            searcher = HybridToolSearcher(
                qdrant_url="http://127.0.0.1:6333",
                max_retries=5,
                retry_delay=1.0,
                backoff_factor=2.0,
            )

        self.assertIs(searcher.client, mock_client)
        self.assertEqual(mock_client.get_collections.call_count, 4)
        self.assertEqual([call.args[0] for call in mock_sleep.call_args_list], [1.0, 2.0, 4.0])
        joined_logs = "\n".join(captured.output)
        self.assertIn("Waiting for Qdrant to be ready (attempt 2/5)...", joined_logs)
        self.assertIn("Waiting for Qdrant to be ready (attempt 4/5)...", joined_logs)

    def test_falls_back_to_collection_exists_probe_when_get_collections_absent(self) -> None:
        class _CollectionExistsOnlyClient:
            def __init__(self) -> None:
                self.calls = 0

            def collection_exists(self, name: str) -> bool:
                self.calls += 1
                if self.calls < 2:
                    raise ConnectionError("not ready")
                return False

        probe_client = _CollectionExistsOnlyClient()
        with (
            patch("src.hybrid_searcher.QdrantClient", return_value=probe_client),
            patch("src.hybrid_searcher.time.sleep") as mock_sleep,
        ):
            searcher = HybridToolSearcher(max_retries=3, retry_delay=0.5)

        self.assertIs(searcher.client, probe_client)
        self.assertEqual(probe_client.calls, 2)
        self.assertEqual([call.args[0] for call in mock_sleep.call_args_list], [0.5])

    def test_raises_clear_connection_error_after_exhausting_retries(self) -> None:
        with (
            patch(
                "src.hybrid_searcher.QdrantClient",
                side_effect=ConnectionError("Connection refused"),
            ) as mock_cls,
            patch("src.hybrid_searcher.time.sleep") as mock_sleep,
            self.assertLogs(level=logging.WARNING) as captured,
        ):
            with self.assertRaises(ConnectionError) as ctx:
                HybridToolSearcher(
                    qdrant_url="http://localhost:6333",
                    max_retries=5,
                    retry_delay=1.0,
                    backoff_factor=2.0,
                    max_retry_delay=16.0,
                )

        self.assertEqual(mock_cls.call_count, 5)
        self.assertEqual(
            [call.args[0] for call in mock_sleep.call_args_list],
            [1.0, 2.0, 4.0, 8.0],
        )
        message = str(ctx.exception)
        self.assertIn("Failed to connect to Qdrant at http://localhost:6333 after 5 attempts", message)
        self.assertIn("docker run -p 6333:6333 qdrant/qdrant", message)
        joined_logs = "\n".join(captured.output)
        self.assertIn("ERROR:root:Failed to connect to Qdrant", joined_logs)

    def test_respects_max_retry_delay_cap_and_config_defaults(self) -> None:
        self.assertEqual(Config.QDRANT_MAX_RETRIES, 5)
        self.assertEqual(Config.QDRANT_RETRY_DELAY, 1.0)
        self.assertEqual(Config.QDRANT_MAX_RETRY_DELAY, 16.0)
        self.assertEqual(Config.QDRANT_BACKOFF_FACTOR, 2.0)

        with (
            patch(
                "src.hybrid_searcher.QdrantClient",
                side_effect=ConnectionError("down"),
            ),
            patch("src.hybrid_searcher.time.sleep") as mock_sleep,
        ):
            with self.assertRaises(ConnectionError):
                HybridToolSearcher(
                    max_retries=4,
                    retry_delay=2.0,
                    backoff_factor=3.0,
                    max_retry_delay=5.0,
                )

        self.assertEqual([call.args[0] for call in mock_sleep.call_args_list], [2.0, 5.0, 5.0])


if __name__ == "__main__":
    unittest.main()
