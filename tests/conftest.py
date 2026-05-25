from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tests must stay deterministic even if the shell was previously configured for
# provider/full mode. Individual tests can still override this with monkeypatch.
os.environ["CHRONORAG_LIGHT"] = "1"
