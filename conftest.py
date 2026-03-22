"""
Pytest configuration and path setup for worker lib.

Ensures that the lib package can be imported from tests.
"""

import sys
from pathlib import Path

# Add the project root to sys.path so that lib module can be imported
project_root = Path(__file__).parent
lib_path = project_root / "lib"

if str(lib_path) not in sys.path:
    sys.path.insert(0, str(project_root))
