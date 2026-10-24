import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import ensure_search_dependencies  # noqa: E402

ensure_search_dependencies()

from src.hybrid_searcher import HybridToolSearcher  # noqa: E402


class TestScoreNormalization(unittest.TestCase):
    """Unit tests for HybridToolSearcher._min_max_scale score normalization."""

    def setUp(self) -> None:
        with patch("src.hybrid_searcher.QdrantClient"):
            self.searcher = HybridToolSearcher()

    def test_min_max_scale_multiple_values(self) -> None:
        """Normalize a dict of distinct scores to [0.0, 1.0]."""
        scores = {
            "tool_1": 10.0,
            "tool_2": 20.0,
            "tool_3": 30.0,
            "tool_4": 40.0,
            "tool_5": 50.0,
        }
        normalized = self.searcher._min_max_scale(scores)

        self.assertAlmostEqual(normalized["tool_1"], 0.0)
        self.assertAlmostEqual(normalized["tool_2"], 0.25)
        self.assertAlmostEqual(normalized["tool_3"], 0.5)
        self.assertAlmostEqual(normalized["tool_4"], 0.75)
        self.assertAlmostEqual(normalized["tool_5"], 1.0)

    def test_min_max_scale_single_value(self) -> None:
        """Single-entry score dictionary normalizes to 1.0."""
        scores = {"only_tool": 25.0}
        normalized = self.searcher._min_max_scale(scores)

        self.assertEqual(normalized, {"only_tool": 1.0})

    def test_min_max_scale_empty_dict(self) -> None:
        """Empty score dictionary returns an empty dictionary."""
        self.assertEqual(self.searcher._min_max_scale({}), {})

    def test_min_max_scale_identical_values(self) -> None:
        """Identical scores avoid division by zero and return 1.0 for every key."""
        scores = {"tool_a": 7.5, "tool_b": 7.5, "tool_c": 7.5}
        normalized = self.searcher._min_max_scale(scores)

        self.assertEqual(normalized, {"tool_a": 1.0, "tool_b": 1.0, "tool_c": 1.0})

    def test_min_max_scale_negative_and_positive_values(self) -> None:
        """Negative and positive scores scale monotonically to [0.0, 1.0]."""
        scores = {"low": -10.0, "mid": 0.0, "high": 10.0}
        normalized = self.searcher._min_max_scale(scores)

        self.assertAlmostEqual(normalized["low"], 0.0)
        self.assertAlmostEqual(normalized["mid"], 0.5)
        self.assertAlmostEqual(normalized["high"], 1.0)


if __name__ == "__main__":
    unittest.main()