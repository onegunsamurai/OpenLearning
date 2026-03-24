GAP_ENRICHMENT_PROMPT_HEADER = """You are a learning engineer analyzing a candidate's skill assessment gaps.

The candidate was assessed at level "{calibrated_level}" targeting "{target_level}".

Here are the identified knowledge gaps (concepts where the candidate falls below the target):
"""

GAP_ENRICHMENT_PROMPT_FOOTER = """
Provide:
1. A "summary": 2-3 sentence executive summary of the candidate's readiness and key areas for improvement.
2. A "recommendations" list with one entry per gap concept. Each recommendation should be a specific, actionable 1-sentence learning suggestion.

Match each recommendation's "concept" field exactly to one of the gap concepts listed above."""
