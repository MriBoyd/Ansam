import unittest
import os
from unittest.mock import patch
import importlib

class TestConfig(unittest.TestCase):
    
    def test_default_config(self):
        # Reload to ensure fresh state
        import src.config
        importlib.reload(src.config)
        from src.config import Config
        
        self.assertEqual(Config.BM25_CANDIDATES, 20)
        self.assertEqual(Config.DENSE_CANDIDATES, 20)
        self.assertEqual(Config.FUSION_CANDIDATES, 4)
        self.assertEqual(Config.FINAL_RESULTS, 1)
        self.assertEqual(Config.FUSION_METHOD, "rrf")

    def test_env_override(self):
        env_vars = {
            "QDRANT_URL": "http://remote:6333",
            "MAX_OPEN_CONNECTIONS": "64",
            "GLOBAL_RATE": "50.0"
        }
        
        with patch.dict(os.environ, env_vars):
            import src.config
            importlib.reload(src.config)
            from src.config import Config
            
            self.assertEqual(Config.QDRANT_URL, "http://remote:6333")
            self.assertEqual(Config.MAX_OPEN_CONNECTIONS, 64)
            self.assertEqual(Config.GLOBAL_RATE, 50.0)

    def test_circuit_breaker_defaults(self):
        import src.config
        importlib.reload(src.config)
        from src.config import Config
        
        self.assertEqual(Config.CB_FAILURE_THRESHOLD, 5)
        self.assertEqual(Config.CB_RECOVERY_TIMEOUT, 30.0)
        self.assertEqual(Config.CB_HALF_OPEN_SUCCESS, 2)

    def test_dotenv_file_loading(self):
        import tempfile
        from dotenv import load_dotenv as real_load_dotenv

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(
                    "QDRANT_URL=http://dotenv-host:6333\n"
                    "QDRANT_COLLECTION=dotenv_tools\n"
                    "MAX_OPEN_CONNECTIONS=48\n"
                )

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("QDRANT_URL", None)
                os.environ.pop("QDRANT_COLLECTION", None)
                os.environ.pop("MAX_OPEN_CONNECTIONS", None)
                with patch(
                    "dotenv.load_dotenv",
                    side_effect=lambda *a, **kw: real_load_dotenv(env_path, *a, **kw),
                ) as mock_load:
                    import src.config

                    importlib.reload(src.config)
                    from src.config import Config

                    mock_load.assert_called_once()
                    self.assertEqual(Config.QDRANT_URL, "http://dotenv-host:6333")
                    self.assertEqual(Config.QDRANT_COLLECTION, "dotenv_tools")
                    self.assertEqual(Config.MAX_OPEN_CONNECTIONS, 48)

    def test_missing_dotenv_fallback(self):
        import sys

        with patch.dict(sys.modules, {"dotenv": None}):
            import src.config

            importlib.reload(src.config)
            from src.config import Config

            self.assertEqual(Config.BM25_CANDIDATES, 20)

if __name__ == "__main__":
    unittest.main()
