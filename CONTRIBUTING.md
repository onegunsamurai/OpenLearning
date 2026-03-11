# Contributing to OpenLearning

Thank you for your interest in contributing to OpenLearning! This guide covers development setup, coding standards, and how to submit changes.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key (optional if using demo mode)

### Installation

```bash
git clone https://github.com/onegunsamurai/OpenLearning.git
cd OpenLearning
make install
```

### Configuration

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env and set ANTHROPIC_API_KEY

# Frontend
cp frontend/.env.example frontend/.env.local
```

### Running Locally

```bash
# Start both frontend and backend
make dev

# Or run them separately
make dev-backend   # http://localhost:8000
make dev-frontend  # http://localhost:3000
```

### Running Tests

```bash
# All checks (lint + typecheck + test)
make check

# Backend tests only
make test

# Format code
make fmt
```

## Code Style

### Python (Backend)

- Formatter/linter: [Ruff](https://docs.astral.sh/ruff/)
- Line length: 100
- Quote style: double quotes
- Run `make fmt` before committing

### TypeScript (Frontend)

- Linter: ESLint with Next.js config
- Strict TypeScript enabled
- Auto-generated API client in `src/lib/generated/` — do not edit manually

## Submitting Changes

### Branch Naming

Use descriptive branch names:
- `feat/user-authentication`
- `fix/assessment-timeout`
- `docs/contributing-guide`
- `kb/frontend-engineering` (for knowledge base contributions)

### Pull Request Process

1. Fork the repository and create your branch from `main`
2. Make your changes with clear, focused commits
3. Ensure all checks pass: `make check`
4. Open a pull request with a clear description of changes
5. Link any related issues

### Commit Messages

Write clear commit messages that explain *why*, not just *what*:
- `feat: add GitHub OAuth login flow`
- `fix: handle Claude API timeout during assessment`
- `docs: add knowledge base contribution guide`
- `kb: add frontend engineering domain`

## Knowledge Base Contributions

One of the easiest ways to contribute is by adding new domain knowledge bases. These are YAML files that define concepts, Bloom taxonomy levels, and prerequisites for a skill domain. **No Python or TypeScript knowledge required.**

### How Knowledge Bases Work

Each knowledge base maps to skills from the taxonomy and defines what concepts a learner should know at each career level (junior, mid, senior, staff). The assessment pipeline uses these to generate targeted questions and evaluate responses.


### Current Domains

- `backend_engineering.yaml` — Backend development concepts

### How to Add a New Domain

1. Create a new YAML file in `backend/app/knowledge_base/`
2. Follow the schema below
3. Map your domain to skill IDs from `backend/app/data/skills_taxonomy.py`
4. Submit a PR using the "Knowledge Base Contribution" issue template

### YAML Schema

```yaml
domain: your_domain_name
mapped_skill_ids:
  - skill-id-1
  - skill-id-2

levels:
  junior:
    concepts:
      - concept: concept_name
        target_confidence: 0.7     # 0.0 to 1.0
        bloom_target: understand   # remember|understand|apply|analyze|evaluate|create
        prerequisites: []          # list of other concept names

  mid:
    concepts:
      - concept: concept_name
        target_confidence: 0.8
        bloom_target: apply
        prerequisites:
          - prerequisite_concept

  senior:
    concepts:
      # Higher Bloom levels, more concepts

  staff:
    concepts:
      # Highest expectations
```

### Guidelines for Knowledge Base PRs

- Each concept should have a clear, specific name (e.g., `http_fundamentals`, not `web_stuff`)
- Prerequisites must reference concepts defined in the same file
- No circular dependencies in prerequisites
- Target confidence should increase with career level
- Bloom targets should generally increase with career level
- Include at least 5 concepts per level

## Issue Labels

| Label | Description |
|-------|-------------|
| `P0` | Critical priority |
| `P1` | High priority |
| `P2` | Normal priority |
| `core-feature` | Core platform functionality |
| `infrastructure` | DevOps, Docker, CI/CD |
| `dx` | Developer experience |
| `community` | Community tooling |
| `good-first-issue` | Good for new contributors |
| `documentation` | Documentation improvements |
| `enhancement` | Improvement to existing feature |

## Questions?

Open an issue or start a discussion. We're happy to help new contributors get started.
