# Used by the assessment pipeline agents (with_structured_output handles format)
PLAN_GEN_PROMPT = """You are a learning engineer creating a personalized learning plan.

The candidate is targeting "{target_level}" level in backend engineering.

Knowledge gaps (sorted by prerequisite order):
{gap_summary}

Create a phased learning plan that:
1. Groups gaps into 3-5 phases, respecting prerequisite order
2. Each phase should build on the previous
3. Include specific resources (real documentation, courses, books)
4. Estimate realistic hours per phase
5. Mix resource types: video, article, project, exercise"""
