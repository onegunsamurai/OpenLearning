# Data Models

This page covers all data structures in the system — Pydantic API models, LangGraph state, database schema, and knowledge graph structures.

## Pydantic API Models

All API models extend `CamelModel`, which serializes field names to camelCase for the frontend.

**Source**: `backend/app/models/`

### Skills

```python
class Skill(CamelModel):
    id: str
    name: str
    category: str
    icon: str
    description: str
    sub_skills: list[str]

class SkillsResponse(CamelModel):
    skills: list[Skill]
    categories: list[str]
```

### Assessment

```python
class Message(CamelModel):
    role: str       # "user" or "assistant"
    content: str

class ProficiencyScore(CamelModel):
    skill_id: str
    skill_name: str
    score: int          # 0-100
    confidence: float   # 0.0-1.0
    reasoning: str

class AssessRequest(CamelModel):
    messages: list[Message]
    skill_names: list[str]
```

### Gap Analysis

```python
class GapItem(CamelModel):
    skill_id: str
    skill_name: str
    current_level: int
    target_level: int
    gap: int
    priority: str       # "critical", "high", "medium", "low"
    recommendation: str

class GapAnalysis(CamelModel):
    overall_readiness: int
    summary: str
    gaps: list[GapItem]

class GapAnalysisRequest(CamelModel):
    proficiency_scores: list[ProficiencyScore]
```

### Learning Plan

```python
class LearningModule(CamelModel):
    id: str
    title: str
    description: str
    type: str             # "theory", "quiz", "lab"
    phase: int
    skill_ids: list[str]
    duration_hours: float
    objectives: list[str]
    resources: list[str]

class Phase(CamelModel):
    phase: int
    name: str
    description: str
    modules: list[LearningModule]

class LearningPlan(CamelModel):
    title: str
    summary: str
    total_hours: float
    total_weeks: int
    phases: list[Phase]

class LearningPlanRequest(CamelModel):
    gap_analysis: GapAnalysis
```

### JD Parser

```python
class JDParseRequest(CamelModel):
    job_description: str

class JDParseResponse(CamelModel):
    skills: list[str]
    summary: str
```

## LangGraph State

The assessment pipeline state is a `TypedDict` that flows through all nodes.

**Source**: `backend/app/graph/state.py`

```python
class AssessmentState(TypedDict, total=False):
    # Session
    candidate_id: str
    skill_ids: list[str]
    skill_domain: str
    target_level: str

    # Calibration
    calibration_questions: list[Question]
    calibration_responses: list[Response]
    calibrated_level: str               # "junior", "mid", "senior", "staff"

    # Assessment loop
    question_history: list[Question]
    response_history: list[Response]
    current_topic: str
    current_bloom_level: BloomLevel
    topics_evaluated: list[str]
    questions_on_current_topic: int
    assessment_complete: bool

    # Evaluation
    latest_evaluation: EvaluationResult

    # Knowledge
    knowledge_graph: KnowledgeGraph
    target_graph: KnowledgeGraph
    gap_nodes: list[KnowledgeNode]
    learning_plan: LearningPlan

    # Human-in-the-loop
    pending_question: Question | None
```

### State Data Types

#### Question

```python
class Question(CamelModel):
    id: str
    topic: str
    bloom_level: BloomLevel
    text: str
    question_type: str  # "conceptual", "scenario", "debugging", "design"
```

#### Response

```python
class Response(CamelModel):
    question_id: str
    text: str
```

#### EvaluationResult

```python
class EvaluationResult(CamelModel):
    question_id: str
    confidence: float       # 0.0-1.0
    bloom_level: BloomLevel
    evidence: list[str]
```

#### BloomLevel

```python
class BloomLevel(StrEnum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyze = "analyze"
    evaluate = "evaluate"
    create = "create"
```

## Knowledge Graph

The knowledge graph tracks what the candidate knows (and doesn't know) about each concept.

**Source**: `backend/app/graph/state.py`

```python
class KnowledgeNode(CamelModel):
    concept: str
    confidence: float       # 0.0-1.0
    bloom_level: BloomLevel
    prerequisites: list[str]
    evidence: list[str]

class KnowledgeGraph(CamelModel):
    nodes: list[KnowledgeNode]
    edges: list[tuple[str, str]]  # (prerequisite, dependent)
```

### Graph Operations

| Method | Description |
|--------|-------------|
| `get_node(concept)` | Find a node by concept name, returns `None` if not found |
| `upsert_node(node)` | Update existing node or append new one |

### Two Graphs

The pipeline maintains two knowledge graphs:

- **`knowledge_graph`** — The candidate's *current* understanding, built from evaluation results
- **`target_graph`** — The *expected* understanding for their target level, loaded from the knowledge base YAML

Gap analysis diffs these two graphs.

## Database Schema

SQLite database with two tables for persisting assessment sessions and results.

**Source**: `backend/app/db.py`

### `assessment_sessions`

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | `String(36)` PK | UUID session identifier |
| `thread_id` | `String(36)` UNIQUE | LangGraph thread identifier |
| `skill_ids` | `JSON` | List of selected skill IDs |
| `target_level` | `String(20)` | Target career level (default: "mid") |
| `status` | `String(20)` | Session status (default: "active") |
| `created_at` | `DateTime` | Creation timestamp |
| `updated_at` | `DateTime` | Last update timestamp |

### `assessment_results`

| Column | Type | Description |
|--------|------|-------------|
| `id` | `Integer` PK | Auto-incrementing ID |
| `session_id` | `String(36)` FK | References `assessment_sessions.session_id` |
| `knowledge_graph` | `JSON` | Final knowledge graph snapshot |
| `gap_nodes` | `JSON` | Identified knowledge gaps |
| `learning_plan` | `JSON` | Generated learning plan |
| `proficiency_scores` | `JSON` | Per-skill proficiency scores |
| `completed_at` | `DateTime` | Completion timestamp |

### Relationship

`AssessmentSession` has a one-to-one relationship with `AssessmentResult` via `session_id`.

### LangGraph Checkpoints

Pipeline state is persisted separately via `AsyncSqliteSaver` in `data/checkpoints.db`. This is managed by LangGraph and stores the full state at each interrupt point, enabling resumption of assessments across server restarts.
