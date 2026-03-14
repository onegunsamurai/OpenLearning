#!/usr/bin/env bash
set -euo pipefail

# Strip the frontend/ prefix so ESLint can resolve paths from within frontend/
files=()
for f in "$@"; do
  files+=("${f#frontend/}")
done

if [ ${#files[@]} -eq 0 ]; then
  exit 0
fi

cd frontend
npx eslint --no-warn-ignored "${files[@]}"
