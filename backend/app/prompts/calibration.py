CALIBRATION_QUESTION_PROMPT = """You are an expert technical interviewer calibrating a candidate's level in {domain}.

Generate a {difficulty} difficulty calibration question about backend engineering.

The question should:
- Be open-ended (not yes/no)
- Test practical understanding, not trivia
- Be answerable in 2-4 sentences
- Cover a {difficulty}-level concept"""


CALIBRATION_EVAL_PROMPT = """You are an expert technical interviewer evaluating calibration responses to determine a candidate's starting level.

The candidate was asked 3 calibration questions (easy, medium, hard) about backend engineering.

Questions and responses:
{qa_pairs}

Based on their responses, determine:
1. Their starting level: "junior", "mid", "senior", or "staff"
2. Initial confidence estimates for relevant concepts (confidence 0.0-1.0, bloom_level as one of: remember, understand, apply, analyze, evaluate, create)
3. The best first topic to assess in depth"""
