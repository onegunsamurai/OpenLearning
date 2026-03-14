# Knowledge Base Guide

Knowledge bases define what concepts a learner should know at each career level for a given skill domain. They are YAML files that drive the entire assessment — from question generation to gap analysis.

**Contributing a knowledge base is the easiest way to contribute to OpenLearning. No Python or TypeScript knowledge required.**

## How Knowledge Bases Work

Each knowledge base:

1. **Maps to skills** from the taxonomy (e.g., `nodejs`, `rest-api`, `sql`)
2. **Defines concepts** organized by career level (junior, mid, senior, staff)
3. **Specifies targets** — the expected confidence and Bloom taxonomy level for each concept
4. **Declares prerequisites** — which concepts depend on others

During assessment, the pipeline:

- Loads the knowledge base to build the **target graph** (what the candidate should know)
- Uses concepts to **generate questions** at the right Bloom level
- Builds the **current graph** from evaluation results
- **Diffs the graphs** to identify gaps

## YAML Schema Reference

```yaml
domain: your_domain_name          # Unique domain identifier (snake_case)
display_name: "Your Domain Name"  # Human-readable name shown in the UI
description: Your domain description  # Brief description of the domain
mapped_skill_ids:                 # Skills from the taxonomy this domain covers
  - skill-id-1
  - skill-id-2

levels:
  junior:
    concepts:
      - concept: concept_name           # Unique concept identifier (snake_case)
        target_confidence: 0.7          # Expected confidence (0.0 to 1.0)
        bloom_target: understand        # Target Bloom level
        prerequisites: []               # List of concept names from this file

  mid:
    concepts:
      - concept: concept_name
        target_confidence: 0.8
        bloom_target: apply
        prerequisites:
          - prerequisite_concept        # Must be defined in the same file

  senior:
    concepts:
      # Higher Bloom levels, more concepts

  staff:
    concepts:
      # Highest expectations
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | Unique domain name in snake_case |
| `display_name` | string | Human-readable name shown in the UI (e.g., "Backend Engineer") |
| `description` | string | Brief description of the domain |
| `mapped_skill_ids` | list[string] | Skill IDs from `backend/app/data/skills_taxonomy.py` |
| `levels` | object | Four career levels, each with a `concepts` list |
| `concept` | string | Unique concept name in snake_case |
| `target_confidence` | float | Expected confidence 0.0–1.0 |
| `bloom_target` | string | One of: `remember`, `understand`, `apply`, `analyze`, `evaluate`, `create` |
| `prerequisites` | list[string] | Concept names that should be learned first |

### Bloom Level Reference

| Level | Verb | What It Means |
|-------|------|---------------|
| `remember` | Recall | Can recall facts and definitions |
| `understand` | Explain | Can explain concepts in own words |
| `apply` | Use | Can apply knowledge to solve problems |
| `analyze` | Compare | Can break down systems and compare approaches |
| `evaluate` | Judge | Can assess trade-offs and make decisions |
| `create` | Design | Can design novel solutions and architectures |

## Walkthrough: Creating a New Domain

Let's create a `frontend_engineering` knowledge base step by step.

### 1. Create the YAML file

Create `backend/app/knowledge_base/frontend_engineering.yaml`:

```yaml
domain: frontend_engineering
display_name: "Frontend Engineer"
description: Frontend engineering concepts from junior to staff level
mapped_skill_ids:
  - javascript
  - typescript
  - react
  - nextjs
  - css
  - html-accessibility
  - state-management
  - testing
  - design-patterns
  - git
  - nodejs
  - rest-api
```

### 2. Define junior concepts

Start with foundational concepts. Junior engineers should *understand* core concepts:

```yaml
levels:
  junior:
    concepts:
      - concept: html_semantics
        target_confidence: 0.7
        bloom_target: understand
        prerequisites: []

      - concept: css_box_model
        target_confidence: 0.7
        bloom_target: understand
        prerequisites: []

      - concept: javascript_fundamentals
        target_confidence: 0.7
        bloom_target: understand
        prerequisites: []

      - concept: dom_manipulation
        target_confidence: 0.6
        bloom_target: understand
        prerequisites:
          - html_semantics
          - javascript_fundamentals

      - concept: react_components
        target_confidence: 0.7
        bloom_target: understand
        prerequisites:
          - javascript_fundamentals
```

### 3. Build up through levels

Each level should:

- Increase Bloom targets (understand → apply → analyze → evaluate)
- Increase target confidence
- Reference prerequisites from earlier levels
- Add more advanced concepts

```yaml
  mid:
    concepts:
      - concept: react_hooks
        target_confidence: 0.8
        bloom_target: apply
        prerequisites:
          - react_components

      - concept: state_management
        target_confidence: 0.8
        bloom_target: apply
        prerequisites:
          - react_hooks

      - concept: css_layout
        target_confidence: 0.8
        bloom_target: apply
        prerequisites:
          - css_box_model
```

### 4. Register the domain

The loader at `backend/app/knowledge_base/loader.py` auto-discovers YAML files by domain name. When skills are selected that map to your domain's `mapped_skill_ids`, the system automatically loads your knowledge base.

The `map_skills_to_domain()` function counts how many of the user's selected skills overlap with each domain's `mapped_skill_ids` and picks the best match.

## Guidelines

### Concept Naming

- Use `snake_case` (e.g., `http_fundamentals`, not `HTTP Fundamentals`)
- Be specific (e.g., `database_indexing`, not `databases`)
- Avoid ambiguity (e.g., `react_hooks` not `hooks`)

### Prerequisites

- Must reference concepts defined in the **same file**
- No circular dependencies
- Keep chains reasonable — avoid deep prerequisite chains (>4 levels)
- Junior concepts should generally have no prerequisites or only reference other junior concepts

### Confidence Targets

- Junior: 0.5–0.7
- Mid: 0.6–0.8
- Senior: 0.7–0.8
- Staff: 0.7–0.8
- Target confidence should generally increase with career level

### Bloom Targets

- Junior: `remember` or `understand`
- Mid: `apply` or `analyze`
- Senior: `analyze` or `evaluate`
- Staff: `evaluate` or `create`
- Bloom targets should generally increase with career level

### Coverage

- Include at least 5 concepts per level
- Cover the breadth of the domain, not just one niche
- Think about what a hiring manager would expect at each level

## Current Domains

| Domain | File | Mapped Skills | Concepts |
|--------|------|---------------|----------|
| Backend Engineering | `backend_engineering.yaml` | nodejs, python, java, go, rest-api, graphql, authentication, microservices, sql, nosql, orm, docker, kubernetes, system-design, testing, design-patterns, monitoring, cicd | 60 concepts across 4 levels |
| Frontend Engineering | `frontend_engineering.yaml` | javascript, typescript, react, nextjs, css, html-accessibility, state-management, testing, design-patterns, git, nodejs, rest-api | 52 concepts across 4 levels |
| DevOps / Platform Engineering | `devops_engineering.yaml` | docker, kubernetes, cicd, aws, monitoring, python, go, system-design, testing, git | 52 concepts across 4 levels |

## Validation

YAML knowledge bases are validated at two levels:

**Pydantic schema validation** — On load, every YAML file is parsed into a `KnowledgeBaseSchema` model (defined in `backend/app/knowledge_base/schema.py`). This validates that all required fields (`domain`, `display_name`, `description`, `mapped_skill_ids`) are present, and that all four career levels (`junior`, `mid`, `senior`, `staff`) exist.

**Automated tests** — `cd backend && pytest tests/test_roles.py` loads every YAML file in the knowledge base directory and validates it against the schema. This catches missing fields, invalid levels, and structural issues automatically in CI.

Before submitting a PR:

1. Ensure your YAML is valid — use a YAML linter or `python -c "import yaml; yaml.safe_load(open('your_file.yaml'))"`
2. Check that all prerequisite references point to concepts defined in the same file
3. Verify no circular dependencies exist
4. Confirm concept names are unique within the file
5. Run `cd backend && pytest tests/test_roles.py -v` to validate against the Pydantic schema
6. Run the full test suite: `make test`

## Submitting Your Contribution

1. Fork the repository
2. Create a branch: `kb/your-domain-name`
3. Add your YAML file to `backend/app/knowledge_base/`
4. Submit a PR using the "Knowledge Base Contribution" issue template
5. Include a brief description of your domain expertise

See [CONTRIBUTING.md](https://github.com/onegunsamurai/OpenLearning/blob/main/CONTRIBUTING.md) for the full contribution workflow.
