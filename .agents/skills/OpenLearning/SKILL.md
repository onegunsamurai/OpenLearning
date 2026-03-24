---
name: openlearning-conventions
description: Development conventions and patterns for OpenLearning. Python project with conventional commits.
---

# Openlearning Conventions

> Generated from [onegunsamurai/OpenLearning](https://github.com/onegunsamurai/OpenLearning) on 2026-03-24

## Overview

This skill teaches Claude the development patterns and conventions used in OpenLearning.

## Tech Stack

- **Primary Language**: Python
- **Architecture**: type-based module organization
- **Test Location**: mixed
- **Test Framework**: vitest

## When to Use This Skill

Activate this skill when:
- Making changes to this repository
- Adding new features following established patterns
- Writing tests that match project conventions
- Creating commits with proper message format

## Commit Conventions

Follow these commit message conventions based on 57 analyzed commits.

### Commit Style: Conventional Commits

### Prefixes Used

- `feat`
- `docs`
- `build`
- `fix`
- `refactor`
- `test`

### Message Guidelines

- Average message length: ~55 characters
- Keep first line concise and descriptive
- Use imperative mood ("Add feature" not "Added feature")


*Commit message example*

```text
docs: update documentation for user dashboard feature
```

*Commit message example*

```text
feat: add user dashboard with assessment history and resume
```

*Commit message example*

```text
fix: add defense-in-depth origin validation for OAuth redirect (#94)
```

*Commit message example*

```text
build(deps-dev): bump @types/node from 20.19.37 to 25.4.0 in /frontend (#4)
```

*Commit message example*

```text
refactor: simplify onboarding UI and update architecture documentation (#62)
```

*Commit message example*

```text
fix: bump react and react-dom together and add dependabot grouping
```

*Commit message example*

```text
feat: implement learning content generation pipeline (#85) (#87)
```

*Commit message example*

```text
docs: add learning content pipeline architecture and fix doc-sync issues
```

## Architecture

### Project Structure: Single Package

This project uses **type-based** module organization.

### Configuration Files

- `.github/workflows/ci.yml`
- `.github/workflows/codeql.yml`
- `.github/workflows/docs.yml`
- `backend/Dockerfile`
- `docker-compose.yml`
- `frontend/Dockerfile`
- `frontend/next.config.ts`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/vitest.config.ts`

### Guidelines

- Group code by type (components, services, utils)
- Keep related functionality in the same type folder
- Avoid circular dependencies between type folders

## Code Style

### Language: Python

### Naming Conventions

| Element | Convention |
|---------|------------|
| Files | camelCase |
| Functions | camelCase |
| Classes | PascalCase |
| Constants | SCREAMING_SNAKE_CASE |

### Import Style: Path Aliases (@/, ~/)

### Export Style: Default Exports


*Preferred import style*

```typescript
// Use path aliases for imports
import { Button } from '@/components/Button'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/lib/api'
```

*Preferred export style*

```typescript
// Use default exports for main component/function
export default function UserProfile() { ... }
```

## Testing

### Test Framework: vitest

### File Pattern: `*.test.tsx`

### Test Types

- **Unit tests**: Test individual functions and components in isolation
- **Integration tests**: Test interactions between multiple components/services

### Mocking: vi.mock


*Test file structure*

```typescript
import { describe, it, expect } from 'vitest'

describe('MyFunction', () => {
  it('should return expected result', () => {
    const result = myFunction(input)
    expect(result).toBe(expected)
  })
})
```

## Error Handling

### Error Handling Style: Try-Catch Blocks


*Standard error handling pattern*

```typescript
try {
  const result = await riskyOperation()
  return result
} catch (error) {
  console.error('Operation failed:', error)
  throw new Error('User-friendly message')
}
```

## Common Workflows

These workflows were detected from analyzing commit patterns.

### Database Migration

Database schema changes with migration files

**Frequency**: ~2 times per month

**Steps**:
1. Create migration file
2. Update schema definitions
3. Generate/update types

**Files typically involved**:
- `**/schema.*`
- `**/types.ts`
- `migrations/*`

**Example commit sequence**:
```
feat: add role-based onboarding and expand knowledge base domains (#40)
docs: Add display_name field to YAML schema
feat: implement offline demo mode with synthetic API and streaming (#42)
```

### Feature Development

Standard feature implementation workflow

**Frequency**: ~18 times per month

**Steps**:
1. Add feature implementation
2. Add tests for feature
3. Update documentation

**Files typically involved**:
- `frontend/src/components/assessment/*`
- `frontend/src/components/gap-analysis/*`
- `frontend/src/components/onboarding/*`
- `**/*.test.*`
- `**/api/**`

**Example commit sequence**:
```
docs: add docs to the README.md
Merge pull request #2 from onegunsamurai/dependabot/github_actions/actions/checkout-6
Merge pull request #1 from onegunsamurai/dependabot/github_actions/actions/setup-python-6
```

### Refactoring

Code refactoring and cleanup workflow

**Frequency**: ~6 times per month

**Steps**:
1. Ensure tests pass before refactor
2. Refactor code structure
3. Verify tests still pass

**Files typically involved**:
- `src/**/*`

**Example commit sequence**:
```
test: add frontend testing suite and CI integration (#32)
feat: add Claude agent infrastructure and project automation rules (#33)
feat: add Docker infrastructure, health check, API updates (#34)
```

### Add Or Update Api Endpoint

Adds a new API endpoint or updates an existing one, including backend route, schema, OpenAPI spec, generated client, frontend usage, and documentation.

**Frequency**: ~3 times per month

**Steps**:
1. Create or update backend route file (backend/app/routes/*.py)
2. Update or add schema/model (backend/app/agents/schemas.py or backend/app/models/*.py)
3. Update OpenAPI spec (backend/openapi.json)
4. Regenerate frontend API client (frontend/src/lib/generated/api-client/*)
5. Update or add tests for the endpoint (backend/tests/test_*.py)
6. Update API reference documentation (docs/guides/api-reference.md)
7. Update data models documentation if needed (docs/architecture/data-models.md)
8. Update or add frontend usage (frontend/src/lib/api.ts, frontend/src/hooks/*, frontend/src/app/*/page.tsx)

**Files typically involved**:
- `backend/app/routes/*.py`
- `backend/app/agents/schemas.py`
- `backend/app/models/*.py`
- `backend/openapi.json`
- `frontend/src/lib/generated/api-client/index.ts`
- `frontend/src/lib/generated/api-client/sdk.gen.ts`
- `frontend/src/lib/generated/api-client/types.gen.ts`
- `backend/tests/test_*.py`
- `docs/guides/api-reference.md`
- `docs/architecture/data-models.md`
- `frontend/src/lib/api.ts`
- `frontend/src/hooks/*.ts`
- `frontend/src/app/*/page.tsx`

**Example commit sequence**:
```
Create or update backend route file (backend/app/routes/*.py)
Update or add schema/model (backend/app/agents/schemas.py or backend/app/models/*.py)
Update OpenAPI spec (backend/openapi.json)
Regenerate frontend API client (frontend/src/lib/generated/api-client/*)
Update or add tests for the endpoint (backend/tests/test_*.py)
Update API reference documentation (docs/guides/api-reference.md)
Update data models documentation if needed (docs/architecture/data-models.md)
Update or add frontend usage (frontend/src/lib/api.ts, frontend/src/hooks/*, frontend/src/app/*/page.tsx)
```

### Feature Development Full Stack

Implements a new feature across backend and frontend, including API, business logic, UI, tests, and documentation.

**Frequency**: ~2 times per month

**Steps**:
1. Implement backend logic (agents, services, pipeline, etc.)
2. Add or update backend routes
3. Update or add database models if needed
4. Update OpenAPI spec
5. Add or update frontend pages/components
6. Add or update frontend hooks and state
7. Integrate frontend with backend API
8. Write backend and frontend tests
9. Update documentation (README, architecture, API reference, data models)

**Files typically involved**:
- `backend/app/agents/*.py`
- `backend/app/services/*.py`
- `backend/app/graph/*.py`
- `backend/app/routes/*.py`
- `backend/app/models/*.py`
- `backend/openapi.json`
- `frontend/src/app/**/*.tsx`
- `frontend/src/components/**/*.tsx`
- `frontend/src/hooks/*.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/store.ts`
- `backend/tests/test_*.py`
- `frontend/src/app/**/*.test.tsx`
- `docs/architecture/*.md`
- `docs/guides/api-reference.md`
- `docs/architecture/data-models.md`
- `README.md`

**Example commit sequence**:
```
Implement backend logic (agents, services, pipeline, etc.)
Add or update backend routes
Update or add database models if needed
Update OpenAPI spec
Add or update frontend pages/components
Add or update frontend hooks and state
Integrate frontend with backend API
Write backend and frontend tests
Update documentation (README, architecture, API reference, data models)
```

### Add Or Update Database Model

Creates or alters a database table or model, updates ORM, generates migrations, and syncs documentation.

**Frequency**: ~2 times per month

**Steps**:
1. Add or update ORM model (backend/app/db.py, backend/app/models/*.py)
2. Create or update migration file (backend/migrations/*.sql)
3. Update database config or connection if needed
4. Update related backend logic (services, routes)
5. Update tests for new/changed model
6. Update data models documentation (docs/architecture/data-models.md)
7. Update setup/testing docs if needed

**Files typically involved**:
- `backend/app/db.py`
- `backend/app/models/*.py`
- `backend/migrations/*.sql`
- `backend/app/services/*.py`
- `backend/app/routes/*.py`
- `backend/tests/test_*.py`
- `docs/architecture/data-models.md`
- `docs/development/setup.md`
- `docs/development/testing.md`

**Example commit sequence**:
```
Add or update ORM model (backend/app/db.py, backend/app/models/*.py)
Create or update migration file (backend/migrations/*.sql)
Update database config or connection if needed
Update related backend logic (services, routes)
Update tests for new/changed model
Update data models documentation (docs/architecture/data-models.md)
Update setup/testing docs if needed
```

### Documentation Sync And Audit

Performs a documentation audit or sync, updating API reference, data models, architecture, and README to match codebase.

**Frequency**: ~3 times per month

**Steps**:
1. Review codebase for changes in endpoints, models, features
2. Update README.md features list and API table
3. Update docs/guides/api-reference.md with new/changed endpoints
4. Update docs/architecture/data-models.md for model changes
5. Update other architecture docs as needed
6. Fix discrepancies, outdated references, or doc-sync issues

**Files typically involved**:
- `README.md`
- `docs/guides/api-reference.md`
- `docs/architecture/data-models.md`
- `docs/architecture/*.md`
- `docs/development/*.md`
- `docs/index.md`

**Example commit sequence**:
```
Review codebase for changes in endpoints, models, features
Update README.md features list and API table
Update docs/guides/api-reference.md with new/changed endpoints
Update docs/architecture/data-models.md for model changes
Update other architecture docs as needed
Fix discrepancies, outdated references, or doc-sync issues
```

### Dependency Or Infrastructure Upgrade

Upgrades dependencies or infrastructure (e.g., npm packages, Docker, GitHub Actions), updates lockfiles/configs, and sometimes fixes related issues.

**Frequency**: ~4 times per month

**Steps**:
1. Update dependency version in package.json/requirements.txt/etc.
2. Update lockfile (package-lock.json, requirements.txt)
3. Update related config files (.github/workflows/*.yml, Dockerfile, docker-compose.yml)
4. Test for compatibility and fix issues if necessary
5. Document any relevant changes if needed

**Files typically involved**:
- `frontend/package.json`
- `frontend/package-lock.json`
- `backend/requirements.txt`
- `.github/workflows/*.yml`
- `Dockerfile`
- `docker-compose.yml`
- `Makefile`

**Example commit sequence**:
```
Update dependency version in package.json/requirements.txt/etc.
Update lockfile (package-lock.json, requirements.txt)
Update related config files (.github/workflows/*.yml, Dockerfile, docker-compose.yml)
Test for compatibility and fix issues if necessary
Document any relevant changes if needed
```

### Add Or Expand Test Coverage

Adds or expands backend and frontend test coverage, often with new test files, shared fixtures, or coverage for new features.

**Frequency**: ~2 times per month

**Steps**:
1. Add or update backend test files (backend/tests/test_*.py, conftest.py)
2. Add or update frontend test files (frontend/src/app/**/*.test.tsx, frontend/src/components/**/*.test.tsx)
3. Update or add shared fixtures/mocks
4. Update documentation to reflect new or changed tests

**Files typically involved**:
- `backend/tests/test_*.py`
- `backend/tests/conftest.py`
- `frontend/src/app/**/*.test.tsx`
- `frontend/src/components/**/*.test.tsx`
- `docs/development/testing.md`

**Example commit sequence**:
```
Add or update backend test files (backend/tests/test_*.py, conftest.py)
Add or update frontend test files (frontend/src/app/**/*.test.tsx, frontend/src/components/**/*.test.tsx)
Update or add shared fixtures/mocks
Update documentation to reflect new or changed tests
```


## Best Practices

Based on analysis of the codebase, follow these practices:

### Do

- Use conventional commit format (feat:, fix:, etc.)
- Write tests using vitest
- Follow *.test.tsx naming pattern
- Use camelCase for file names
- Prefer default exports

### Don't

- Don't use long relative imports (use aliases)
- Don't write vague commit messages
- Don't skip tests for new features
- Don't deviate from established patterns without discussion

---

*This skill was auto-generated by [ECC Tools](https://ecc.tools). Review and customize as needed for your team.*
