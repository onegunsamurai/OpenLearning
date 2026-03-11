# API Reference

The OpenLearning API is a FastAPI application serving at `http://localhost:8000`. Interactive Swagger docs are available at [`/api/docs`](http://localhost:8000/api/docs).

## Endpoints

### GET `/api/skills`

Returns the full skills taxonomy with categories.

**Response**: `SkillsResponse`

```json
{
  "skills": [
    {
      "id": "nodejs",
      "name": "Node.js",
      "category": "Backend",
      "icon": "...",
      "description": "...",
      "subSkills": ["Express", "Fastify"]
    }
  ],
  "categories": ["Backend", "Frontend", "DevOps"]
}
```

---

### POST `/api/parse-jd`

Extract skills from a job description using AI.

**Request**: `JDParseRequest`

```json
{
  "jobDescription": "We're looking for a senior backend engineer with experience in Node.js, PostgreSQL, and Kubernetes..."
}
```

**Response**: `JDParseResponse`

```json
{
  "skills": ["nodejs", "sql", "kubernetes"],
  "summary": "Senior backend role focusing on Node.js services with PostgreSQL and K8s infrastructure."
}
```

---

### POST `/api/assessment/start`

Start a new assessment session. Returns the first calibration question.

**Request body**:

```json
{
  "skillIds": ["nodejs", "rest-api", "sql"],
  "targetLevel": "mid"
}
```

**Response** (SSE stream): The first calibration question as a JSON event.

---

### POST `/api/assessment/{session_id}/respond`

Submit an answer and receive the next question (or completion).

**Request body**:

```json
{
  "answer": "HTTP is a stateless protocol that uses request-response pairs..."
}
```

**Response** (SSE stream): Events include:

| Event | Description |
|-------|-------------|
| Question event | Next question with metadata (topic, Bloom level, progress) |
| Metadata event | Assessment progress (topics evaluated, total questions) |
| Completion event | Assessment complete with proficiency scores |

---

### GET `/api/assessment/{session_id}/graph`

Get the current knowledge graph for an assessment session.

**Response**: Knowledge graph with nodes and edges.

```json
{
  "nodes": [
    {
      "concept": "http_fundamentals",
      "confidence": 0.85,
      "bloomLevel": "apply",
      "prerequisites": [],
      "evidence": ["Demonstrated understanding of HTTP methods", "..."]
    }
  ],
  "edges": [["http_fundamentals", "rest_api_basics"]]
}
```

---

### GET `/api/assessment/{session_id}/report`

Get the full assessment report. Stores results in the database (idempotent).

**Response**: Full report including knowledge graph, gap nodes, learning plan, and proficiency scores.

---

### POST `/api/gap-analysis`

Generate a gap analysis from proficiency scores.

**Request**: `GapAnalysisRequest`

```json
{
  "proficiencyScores": [
    {
      "skillId": "nodejs",
      "skillName": "Node.js",
      "score": 65,
      "confidence": 0.8,
      "reasoning": "Strong fundamentals, gaps in advanced patterns"
    }
  ]
}
```

**Response**: `GapAnalysis`

```json
{
  "overallReadiness": 72,
  "summary": "Solid foundation with gaps in distributed systems and security.",
  "gaps": [
    {
      "skillId": "microservices",
      "skillName": "Microservices",
      "currentLevel": 45,
      "targetLevel": 80,
      "gap": 35,
      "priority": "critical",
      "recommendation": "Focus on service decomposition and inter-service communication patterns."
    }
  ]
}
```

Priority levels: `critical` (gap > 40), `high` (gap > 25), `medium` (gap > 10), `low` (gap <= 10).

---

### POST `/api/learning-plan`

Generate a personalized learning plan from gap analysis.

**Request**: `LearningPlanRequest`

```json
{
  "gapAnalysis": {
    "overallReadiness": 72,
    "summary": "...",
    "gaps": [...]
  }
}
```

**Response**: `LearningPlan`

```json
{
  "title": "Backend Engineering Growth Plan",
  "summary": "A 6-week plan targeting distributed systems and security gaps.",
  "totalHours": 48,
  "totalWeeks": 6,
  "phases": [
    {
      "phase": 1,
      "name": "Foundations",
      "description": "...",
      "modules": [
        {
          "id": "mod-1",
          "title": "Microservices Fundamentals",
          "description": "...",
          "type": "theory",
          "phase": 1,
          "skillIds": ["microservices"],
          "durationHours": 4,
          "objectives": ["Understand service decomposition", "..."],
          "resources": ["https://microservices.io/patterns"]
        }
      ]
    }
  ]
}
```

## Assessment Flow

The full assessment flow involves multiple API calls:

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant LangGraph

    Client->>API: POST /assessment/start
    API->>LangGraph: Initialize pipeline
    LangGraph-->>API: Calibration Q1 (interrupt)
    API-->>Client: SSE: calibration question

    Client->>API: POST /assessment/{id}/respond
    API->>LangGraph: Resume with answer
    LangGraph-->>API: Calibration Q2 (interrupt)
    API-->>Client: SSE: calibration question

    Note over Client,LangGraph: ...repeat for Q3 and evaluation...

    Client->>API: POST /assessment/{id}/respond
    API->>LangGraph: Resume with answer
    LangGraph-->>API: Assessment question (interrupt)
    API-->>Client: SSE: assessment question

    Note over Client,LangGraph: ...assessment loop continues...

    Client->>API: POST /assessment/{id}/respond
    API->>LangGraph: Resume with final answer
    LangGraph-->>API: Pipeline complete
    API-->>Client: SSE: completion + scores

    Client->>API: GET /assessment/{id}/report
    API-->>Client: Full report (graph, gaps, plan)
```

## SSE Streaming

The `/assessment/start` and `/assessment/{id}/respond` endpoints use Server-Sent Events (SSE) for streaming responses. The frontend receives events as they're generated, enabling real-time display of questions and progress updates.

## Swagger Documentation

For the full interactive API documentation with request/response schemas, run the backend and visit:

**[http://localhost:8000/api/docs](http://localhost:8000/api/docs)**
