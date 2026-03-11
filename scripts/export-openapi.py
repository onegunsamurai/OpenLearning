#!/usr/bin/env python3
"""Export the FastAPI OpenAPI spec to a static JSON file.

Usage:
    python scripts/export-openapi.py [output_path]

The default output path is backend/openapi.json.
"""

import json
import sys
from pathlib import Path

# Ensure the backend package is importable
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.main import app  # noqa: E402

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "backend" / "openapi.json"


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_PATH
    spec = app.openapi()
    output.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"OpenAPI spec written to {output}")


if __name__ == "__main__":
    main()
