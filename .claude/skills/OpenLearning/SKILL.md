---
name: openlearning-conventions
description: Development conventions and patterns for OpenLearning. Python project with conventional commits.
---

# Openlearning Conventions

> Generated from [onegunsamurai/OpenLearning](https://github.com/onegunsamurai/OpenLearning) on 2026-03-23

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

Follow these commit message conventions based on 8 analyzed commits.

### Commit Style: Conventional Commits

### Prefixes Used

- `feat`
- `docs`
- `build`
- `fix`
- `refactor`
- `test`

### Message Guidelines

- Average message length: ~54 characters
- Keep first line concise and descriptive
- Use imperative mood ("Add feature" not "Added feature")


*Commit message example*

```text
docs: add learning content pipeline architecture and fix doc-sync issues
```

*Commit message example*

```text
feat: test claude architecure update
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
fix: resolve frontend proxy networking in docker environment (#61)
```

*Commit message example*

```text
feat: add email/password auth with register and login endpoints (#83)
```

*Commit message example*

```text
docs: discord perma-link
```

*Commit message example*

```text
docs: add Discord bage
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

**Frequency**: ~5 times per month

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
feat: add Docker infrastructure, health check, API updates (#34)
fix: docker-compose cors env
feat: implement pre-commit hooks for automated code quality checks (#36)
```

### Feature Development

Standard feature implementation workflow

**Frequency**: ~17 times per month

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
docs: add contribution guidelines, templates, and project metadata
docs: add comprehensive documentation site and deployment pipeline
fix: gitleaks fetch depth
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
