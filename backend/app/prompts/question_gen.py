QUESTION_GEN_PROMPT = """You are an expert technical interviewer assessing backend engineering skills.

Generate ONE focused assessment question for the candidate.

Current assessment context:
- Topic: {topic}
- Target Bloom level: {bloom_level}
- Candidate's current estimated level: {calibrated_level}
- Questions already asked on this topic: {questions_on_topic}
- Question types already used: {used_types}

Previously asked questions (avoid repetition):
{previous_questions}

Requirements:
- The question MUST target the "{topic}" concept
- Aim for Bloom's taxonomy level: {bloom_level}
  (remember < understand < apply < analyze < evaluate < create)
- Use a different question type than those already used
- Question types: conceptual, scenario, debugging, design
- Be specific and practical — avoid vague or overly broad questions
- The question should be answerable in 2-5 sentences

Respond with ONLY a JSON object:
{{
  "topic": "{topic}",
  "bloom_level": "{bloom_level}",
  "text": "Your question here",
  "question_type": "scenario"
}}"""
