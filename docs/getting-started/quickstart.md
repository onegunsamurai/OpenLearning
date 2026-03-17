# Quick Start

This walkthrough guides you through a complete assessment cycle — from skill selection to a personalized learning plan.

## Step 1: Select Skills

On the onboarding page, you have two options:

**Option A — Select a role** (recommended): Choose a predefined role (e.g., Backend Engineer, Frontend Engineer, DevOps / Platform Engineer). This automatically selects the relevant skills and maps to the correct knowledge base domain.

**Option B — Browse and select**: Browse the skills taxonomy by category and select the skills you want to be assessed on.

!!! info
    Skills map to knowledge base domains. Three domains are fully supported with comprehensive concept hierarchies: Backend Engineering, Frontend Engineering, and DevOps / Platform Engineering.

## Step 2: Calibration

The assessment begins with **3 calibration questions** at increasing difficulty (easy, medium, hard). These determine your starting level:

| Calibrated Level | Starting Bloom Level | Description |
|-----------------|---------------------|-------------|
| Junior | Understand | Foundational concepts |
| Mid | Apply | Practical application |
| Senior | Analyze | System-level reasoning |
| Staff | Evaluate | Architecture and strategy |

The calibrator also identifies initial concepts for your knowledge graph and picks the first topic to assess.

## Step 3: Adaptive Assessment

The main assessment loop generates questions tailored to your demonstrated level:

1. **Question generation** — Claude generates a question targeting your current topic and Bloom level
2. **Your response** — Answer the question in the chat interface
3. **Evaluation** — Claude evaluates your response for accuracy, depth, and demonstrated Bloom level
4. **Knowledge graph update** — Your confidence score is updated (weighted: 70% existing + 30% new evidence)
5. **Routing** — The system decides what to do next:
    - **Deeper**: You showed high confidence — advance to a harder Bloom level
    - **Probe**: Decent answer but needs more evidence — ask a follow-up
    - **Pivot**: Confidence established (high or low) — move to the next topic
    - **Conclude**: Enough coverage — proceed to gap analysis

The assessment continues until **8 topics** have been evaluated or **25 questions** have been asked.

## Step 4: Gap Analysis

After the assessment completes, the system compares your knowledge graph against the target graph for your chosen level. Gaps are identified where your confidence is more than 0.2 below the target, then sorted by prerequisite order.

You'll see a radar chart comparing current vs. target proficiency across all assessed concepts, plus a priority-ranked list of gaps.

## Step 5: Learning Plan

Finally, a personalized learning plan is generated from your gaps. The plan includes:

- **Phased structure** — Concepts grouped into 3-5 phases respecting prerequisite order
- **Mixed resources** — Articles, videos, hands-on projects, and exercises
- **Time estimates** — Realistic hour estimates per phase
- **Rationale** — Why concepts are grouped and ordered the way they are

## What's Happening Under the Hood

The entire flow is powered by a LangGraph state machine with human-in-the-loop interrupts. Each time you answer a question, the graph resumes from a checkpoint, processes your response, and determines the next step.

See [Assessment Pipeline](../architecture/assessment-pipeline.md) for the full technical deep-dive.
