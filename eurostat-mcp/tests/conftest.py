"""Ensure eurostat-mcp/ is importable regardless of CWD or PYTHONPATH."""

import sys
from pathlib import Path

_MCP_DIR = Path(__file__).resolve().parent.parent
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))
