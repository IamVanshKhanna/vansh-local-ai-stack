"""Allow running the CLI via ``python .`` or ``python -m vansh_local_ai_stack``."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so relative imports work
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from vls import main

if __name__ == "__main__":
    main()
