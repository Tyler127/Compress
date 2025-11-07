"""Backward-compatible entry point for running Compressy as a script."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


if __name__ != "__main__":
    # When imported (e.g., `import compressy`), delegate to the real package
    package_dir = Path(__file__).resolve().parent / "compressy"
    if package_dir.is_dir():
        __path__ = [str(package_dir)]  # type: ignore[var-annotated]

    package = importlib.import_module("compressy.__init__")
    sys.modules[__name__] = package
else:  # pragma: no cover
    from compressy.cli import main as _main

    raise SystemExit(_main())
