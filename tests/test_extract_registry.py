import unittest
from unittest.mock import patch, MagicMock
import sys
import os

from src import extract_registry
from src.scripts import mcp_crawler

class TestExtractRegistry(unittest.TestCase):
    
    @patch("subprocess.run")
    def test_main_execution(self, mock_run):
        # We need to simulate running extract_registry.py as a script
        # Mock sys.argv
        with patch.object(sys, 'argv', ['extract_registry.py', '--name', 'test_server', '--transport', 'stdio', '--command', 'node']):
            extract_registry.main()
            
            # The script calls subprocess.run with a list that includes the path to mcp_registry_manager.py
            # and our forwarded args
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("mcp_registry_manager.py", args[1])
            self.assertTrue(os.path.exists(args[1]))
            self.assertIn("--name", args)
            self.assertIn("test_server", args)
            self.assertIn("--output", args)
            self.assertIn("mcp_servers.json", args)

    @patch("subprocess.run")
    def test_mcp_crawler_execution(self, mock_run):
        with patch.object(sys, 'argv', ['mcp_crawler.py', '--name', 'crawler_server']):
            mcp_crawler.main()

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("mcp_registry_manager.py", args[1])
            self.assertTrue(os.path.exists(args[1]), f"Path {args[1]} does not exist on disk")
            self.assertIn("--mode", args)
            self.assertIn("flat", args)
            self.assertIn("--output", args)
            self.assertIn("registry_dump.json", args)

if __name__ == "__main__":
    unittest.main()
