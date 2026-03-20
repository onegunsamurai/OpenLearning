# Code Style

## Python (Backend)

### Formatter and Linter

The backend uses [Ruff](https://docs.astral.sh/ruff/) for both formatting and linting.

**Configuration**: `backend/pyproject.toml`

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501", "B008", "RUF012"]

[tool.ruff.lint.per-file-ignores]
"app/main.py" = ["E402"]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.ruff.format]
quote-style = "double"
```

### Rules

| Code | Category | Description |
|------|----------|-------------|
| `E` | pycodestyle errors | Basic style errors |
| `W` | pycodestyle warnings | Style warnings |
| `F` | pyflakes | Logical errors, unused imports |
| `I` | isort | Import sorting |
| `UP` | pyupgrade | Python version upgrades |
| `B` | flake8-bugbear | Common bug patterns |
| `SIM` | flake8-simplify | Code simplification |
| `RUF` | Ruff-specific | Ruff's own rules |

### Commands

```bash
# Format code
make fmt

# Check linting (no auto-fix)
make lint-backend
```

### Key Conventions

- **Line length**: 100 characters
- **Quotes**: Double quotes (`"`)
- **Imports**: Sorted by isort (stdlib → third-party → local)
- **Type hints**: Use modern syntax (`list[str]` not `List[str]`, `str | None` not `Optional[str]`)
- **Async**: Use `async`/`await` for all I/O operations

## TypeScript (Frontend)

### Linter

The frontend uses [ESLint](https://eslint.org/) with the Next.js configuration.

**Configuration**: `frontend/eslint.config.mjs`

```javascript
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_" },
      ],
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "src/lib/generated/**",
  ]),
]);

export default eslintConfig;
```

### Commands

```bash
# Lint frontend
make lint-frontend

# Type check
make typecheck
```

### Key Conventions

- **Strict TypeScript**: Enabled in `tsconfig.json`
- **ESLint**: Core Web Vitals + TypeScript rules
- **Imports**: Use absolute imports from `@/` (maps to `src/`)

## Auto-Generated Code

Files in `frontend/src/lib/generated/` are auto-generated from the backend OpenAPI spec.

!!! warning
    **Do not edit files in `src/lib/generated/` manually.** They are overwritten by `make generate-api`.

To regenerate after backend model changes:

```bash
# With backend running
make generate-api
```

## General Conventions

- **Commit messages**: Use conventional format — `feat:`, `fix:`, `docs:`, `kb:`, etc.
- **Branch names**: Descriptive with prefixes — `feat/`, `fix/`, `docs/`, `kb/`
- **Run `make check` before committing** to catch lint, type, and test issues early
