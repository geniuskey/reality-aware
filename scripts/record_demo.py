#!/usr/bin/env python3
"""Record the demo figures and the episode GIF used on the Demo page.

A thin wrapper over `python -m nano.demo`, which is the interface the
documentation quotes; this exists because the figures name it as their producer.
"""

from __future__ import annotations

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from nano.demo import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
