import os
import statistics
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_hybrid_searcher import create_benchmark_searcher  # noqa: E402


def benchmark_search_performance() -> dict:
    """Benchmark search performance with 100 tools against the current HybridToolSearcher API."""
    searcher, large_tools = create_benchmark_searcher()

    index_times = []
    search_times = []
    exact_times = []

    # Warm up
    searcher.index(large_tools, recreate=True)

    for _ in range(10):
        # Incremental index time (fast when points are already indexed)
        start_index = time.time()
        searcher.index(large_tools, recreate=False)
        index_times.append(time.time() - start_index)

        # Semantic Search time
        start_search = time.time()
        searcher.search("find a tool for data analysis", limit=5)
        search_times.append(time.time() - start_search)

        # Exact Match time
        start_exact = time.time()
        searcher.search("tool_5", limit=5)
        exact_times.append(time.time() - start_exact)

    summary = {
        "index_mean": statistics.mean(index_times),
        "search_mean": statistics.mean(search_times),
        "exact_mean": statistics.mean(exact_times),
    }
    print("\nBenchmark Results (100 tools):")
    print(f"Index Mean: {summary['index_mean']:.3f}s")
    print(f"Semantic Search Mean: {summary['search_mean']:.3f}s")
    print(f"Exact Match Mean: {summary['exact_mean']:.3f}s")
    return summary


def test_benchmark_search_performance() -> None:
    summary = benchmark_search_performance()
    assert summary["index_mean"] < 10.0
    assert summary["search_mean"] < 5.0
    assert summary["exact_mean"] < 5.0


if __name__ == "__main__":
    benchmark_search_performance()
