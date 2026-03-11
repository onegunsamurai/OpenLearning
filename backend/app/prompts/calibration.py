CALIBRATION_QUESTION_PROMPT = """You are an expert technical interviewer calibrating a candidate's level in {domain}.

Generate a {difficulty} difficulty calibration question about backend engineering.

The question should:
- Be open-ended (not yes/no)
- Test practical understanding, not trivia
- Be answerable in 2-4 sentences
- Cover a {difficulty}-level concept

Respond with ONLY a JSON object:
{{
  "topic": "the_concept_being_tested",
  "text": "The question text",
  "question_type": "conceptual"
}}"""


CALIBRATION_EVAL_PROMPT = """You are an expert technical interviewer evaluating calibration responses to determine a candidate's starting level.

The candidate was asked 3 calibration questions (easy, medium, hard) about backend engineering.

Questions and responses:
{qa_pairs}

Based on their responses, determine:
1. Their starting level: "junior", "mid", "senior", or "staff"
2. Initial confidence estimates for relevant concepts
3. The best first topic to assess in depth

Respond with ONLY a JSON object:
{{
  "calibrated_level": "mid",
  "initial_concepts": [
    {{
      "concept": "concept_name",
      "confidence": 0.5,
      "bloom_level": "understand"
    }}
  ],
  "first_topic": "concept_to_assess_first",
  "reasoning": "Brief explanation of level determination"
}}"""
