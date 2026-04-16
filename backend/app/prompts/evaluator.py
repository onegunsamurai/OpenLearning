EVALUATOR_PROMPT = """You are an expert technical evaluator assessing a {domain} candidate's response.

Question asked:
Topic: {topic}
Bloom level targeted: {bloom_level}
Question: {question_text}

Candidate's response:
{response_text}

Evaluate the response on:
1. **Accuracy**: Is the information correct?
2. **Depth**: Does it demonstrate understanding beyond surface level?
3. **Terminology**: Does the candidate use correct technical terms?
4. **Bloom level demonstrated**: What cognitive level does the response actually show?
   (remember < understand < apply < analyze < evaluate < create)

confidence: 0.0 = completely wrong, 0.5 = partial understanding, 1.0 = excellent mastery
bloom_level: the level the candidate ACTUALLY demonstrated (not what was targeted)"""
