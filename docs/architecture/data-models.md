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
class ProficiencyScore(CamelModel):
    skill_id: str
    skill_name: str
    score: int          # 0-100
    confidence: float   # 0.0-1.0
    reasoning: str
```

### Gap Analysis

```python
class GapItem(CamelModel):
    skill_id: str
    skill_name: str
    current_level: int
    target_level: int
    gap: int
    priority: Literal["critical", "high", "medium", "low"]
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
    type: Literal["theory", "quiz", "lab"]
    phase: int
    skill_ids: list[str]
    duration_hours: int
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
    total_hours: int
    total_weeks: int
    phases: list[Phase]

class LearningPlanRequest(CamelModel):
    gap_analysis: GapAnalysis
```

### Roles

```python
class RoleLevelSummary(CamelModel):
    name: str
    concept_count: int

class RoleSummary(CamelModel):
    id: str
    name: str
    description: str
    skill_count: int
    levels: list[str]

class RoleDetail(CamelModel):
    id: str
    name: str
    description: str
    mapped_skill_ids: list[str]
    levels: list[RoleLevelSummary]
```

**Source**: `backend/app/models/roles.py`

### Assessment Route Models

These are simplified output projections defined directly in the route module (not in `models/`). They differ from the pipeline state types in `graph/state.py`.

**Source**: `backend/app/routes/assessment.py`

```python
# Request/Response for /assessment/start
class AssessmentStartRequest(CamelModel):
    skill_ids: list[str]
    target_level: str = "mid"
    role_id: str | None = None  # Validated: must be in list_domains() or None

class AssessmentRespondRequest(CamelModel):
    response: str

class AssessmentStartResponse(CamelModel):
    session_id: str
    question: str
    question_type: str = "calibration"
    step: int = 1
    total_steps: int = 3

# Response for /assessment/{id}/graph
class KnowledgeNodeOut(CamelModel):
    concept: str
    confidence: float
    bloom_level: str
    prerequisites: list[str]

class KnowledgeGraphOut(CamelModel):
    nodes: list[KnowledgeNodeOut]

class ProficiencyScoreOut(CamelModel):
    skill_id: str
    skill_name: str
    score: int
    confidence: float
    reasoning: str

class ResourceOut(CamelModel):
    type: str
    title: str
    url: str | None = None

class LearningPhaseOut(CamelModel):
    phase_number: int
    title: str
    concepts: list[str]
    rationale: str
    resources: list[ResourceOut]
    estimated_hours: float

# Response for /assessment/{id}/report
class GapNodeOut(CamelModel):
    concept: str
    current_confidence: float
    target_bloom_level: str
    prerequisites: list[str]

class LearningPlanOut(CamelModel):
    summary: str
    total_hours: float
    phases: list[LearningPhaseOut]

class AssessmentReportResponse(CamelModel):
    knowledge_graph: KnowledgeGraphOut
    gap_nodes: list[GapNodeOut]
    learning_plan: LearningPlanOut
    proficiency_scores: list[ProficiencyScoreOut]
```

### Auth Route Models

These are defined directly in the route module (not in `models/`), following the same pattern as the assessment route models above.

**Source**: `backend/app/routes/auth.py`

```python
class AuthMeResponse(CamelModel):
    user_id: str
    github_username: str
    avatar_url: str
    has_api_key: bool

class ApiKeySetRequest(CamelModel):
    api_key: str

class ApiKeyResponse(CamelModel):
    api_key_preview: str
```

### Knowledge Base Schema

These models validate YAML knowledge base files on load. They use `BaseModel` (not `CamelModel`) because they are internal, not API-facing.

```python
LEVEL_ORDER: list[str] = ["junior", "mid", "senior", "staff"]

class ConceptSchema(BaseModel):
    concept: str
    target_confidence: float
    bloom_target: str
    prerequisites: list[str] = []

class LevelSchema(BaseModel):
    concepts: list[ConceptSchema]

class KnowledgeBaseSchema(BaseModel):
    domain: str
    display_name: str
    description: str
    mapped_skill_ids: list[str]
    levels: dict[str, LevelSchema]

    @field_validator("levels")
    @classmethod
    def must_have_all_levels(cls, v: dict) -> dict:
        """Validates that all four levels (junior, mid, senior, staff) are present."""
        required = set(LEVEL_ORDER)
        missing = required - v.keys()
        if missing:
            raise ValueError(f"Missing levels: {missing}")
        return v
```

**Source**: `backend/app/knowledge_base/schema.py`

### Health

```python
class HealthResponse(BaseModel):  # Note: extends BaseModel, not CamelModel
    status: str
    database: str | None = None
```

**Source**: `backend/app/models/health.py`

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
    learning_plan: LearningPlan   # state.py LearningPlan (see below)

    # Human-in-the-loop
    pending_question: Question | None
```

!!! note "Pipeline vs API `LearningPlan`"
    The `learning_plan` field in `AssessmentState` uses the **pipeline** `LearningPlan` defined in `graph/state.py`, which has different fields from the API model in `models/learning_plan.py`:

    ```python
    # graph/state.py — used inside the pipeline
    class LearningPlan(CamelModel):
        phases: list[LearningPhase]
        total_hours: float
        summary: str

    class LearningPhase(CamelModel):
        phase_number: int
        title: str
        concepts: list[str]
        rationale: str
        resources: list[Resource]
        estimated_hours: float

    class Resource(CamelModel):
        type: str   # "video", "article", "project", "exercise"
        title: str
        url: str | None = None
    ```

    The API `LearningPlan` (in `models/learning_plan.py`) has `title`, `total_weeks`, `total_hours: int`, and `phases: list[Phase]`. The pipeline version omits `title`/`total_weeks`, uses `float` for hours, and structures phases differently.

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
    prerequisites: list[str] = []
    evidence: list[str] = []

class KnowledgeGraph(CamelModel):
    nodes: list[KnowledgeNode] = []
    edges: list[tuple[str, str]] = []  # (prerequisite, dependent)
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

## LLM Output Schemas

These Pydantic models define the contract between the LLM and the assessment agents. They use plain `BaseModel` (not `CamelModel`) because they are internal to the LLM integration — the LLM returns data in this shape, and agents map it to the `CamelModel` state types.

**Source**: `backend/app/agents/schemas.py`

### Calibration

```python
class CalibrationQuestionOutput(BaseModel):
    topic: str           # Technical concept being tested
    text: str            # The question text
    question_type: str   # "conceptual", "scenario", "debugging", "design"

class CalibrationEvalConcept(BaseModel):
    concept: str         # Concept name
    confidence: float    # 0.0–1.0
    bloom_level: str     # Bloom taxonomy level

class CalibrationEvalOutput(BaseModel):
    calibrated_level: str                        # "junior", "mid", "senior", "staff"
    initial_concepts: list[CalibrationEvalConcept]
    first_topic: str                             # Best first topic for in-depth assessment
    reasoning: str                               # Explanation of level determination
```

### Question Generation

```python
class QuestionOutput(BaseModel):
    topic: str           # Technical concept being tested
    bloom_level: str     # Target Bloom taxonomy level
    text: str            # The question text
    question_type: str   # "conceptual", "scenario", "debugging", "design"
```

### Response Evaluation

```python
class EvaluationOutput(BaseModel):
    confidence: float    # 0.0 = wrong, 0.5 = partial, 1.0 = excellent
    bloom_level: str     # Bloom level actually demonstrated
    evidence: list[str]  # Specific observations
    reasoning: str       # Brief overall assessment
```

### Learning Plan

```python
class PlanResourceOutput(BaseModel):
    type: str            # "video", "article", "project", "exercise"
    title: str
    url: str | None

class PlanPhaseOutput(BaseModel):
    phase_number: int
    title: str
    concepts: list[str]
    rationale: str
    resources: list[PlanResourceOutput]
    estimated_hours: float

class PlanOutput(BaseModel):
    summary: str
    total_hours: float
    phases: list[PlanPhaseOutput]
```

## Database Schema

SQLite database with three tables for persisting users, assessment sessions, and results.

**Source**: `backend/app/db.py`

### `users`

| Column | Type | Description |
|--------|------|-------------|
| `id` | `String(36)` PK | UUID user identifier |
| `github_id` | `BigInteger` UNIQUE | GitHub user ID |
| `github_username` | `String(39)` | GitHub username |
| `avatar_url` | `String(500)` | GitHub avatar URL |
| `encrypted_api_key` | `String(500)` NULL | Fernet-encrypted Anthropic API key |
| `created_at` | `DateTime` | Creation timestamp |
| `updated_at` | `DateTime` | Last update timestamp |

### `assessment_sessions`

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | `String(36)` PK | UUID session identifier |
| `thread_id` | `String(36)` UNIQUE | LangGraph thread identifier |
| `skill_ids` | `JSON` | List of selected skill IDs |
| `target_level` | `String(20)` | Target career level (default: "mid") |
| `status` | `String(20)` | Session status: `"active"`, `"completed"`, or `"timed_out"` (default: `"active"`) |
| `user_id` | `String(36)` FK NULL | References `users.id` |
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

### Relationships

- `User` → `AssessmentSession`: one-to-many via `user_id`
- `AssessmentSession` → `AssessmentResult`: one-to-one via `session_id`

### LangGraph Checkpoints

Pipeline state is persisted separately via `AsyncSqliteSaver` in `data/checkpoints.db`. This is managed by LangGraph and stores the full state at each interrupt point, enabling resumption of assessments across server restarts.
