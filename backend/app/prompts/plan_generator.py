# Used by the assessment pipeline agents (with_structured_output handles format)
PLAN_GEN_PROMPT = """You are a learning engineer creating a personalized learning plan.

The candidate is targeting "{target_level}" level as a {domain}.

Knowledge gaps (sorted by prerequisite order):
{gap_summary}

Create a phased learning plan that:
1. Groups gaps into 3-5 phases, respecting prerequisite order.
2. Each phase should build on the previous.
3. Estimate realistic hours per phase.
4. Within each phase, break the work into concrete concepts. Each concept must
   carry its own 2-4 learning resources (real documentation, courses, books,
   projects). Do NOT emit phase-level resources — resources always live on a
   concept.
5. Each concept also carries a 1-2 sentence `description` explaining why it
   matters for the phase goal.
6. Mix resource types across a phase: video, article, project, exercise.

Example concept shape:
  {{"name": "Async I/O fundamentals",
    "description": "Understand the event loop and why I/O-bound work benefits from async.",
    "resources": [
      {{"type": "article", "title": "Python asyncio basics", "url": "..."}},
      {{"type": "project", "title": "Build a tiny async HTTP client", "url": null}}
    ]}}"""
