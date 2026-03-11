#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Exporting OpenAPI spec from FastAPI..."
python "$SCRIPT_DIR/export-openapi.py"

echo "Generating TypeScript client from OpenAPI spec..."
cd "$ROOT_DIR/frontend"
npm run generate-api

echo "Done! Generated client is in frontend/src/lib/generated/api-client/"
