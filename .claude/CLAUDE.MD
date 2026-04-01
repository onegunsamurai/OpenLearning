# Project rules (always active)

## Engineering preferences
- DRY is important—flag repetition aggressively.
- Well-tested code is non-negotiable.
- "Engineered enough" — not under-engineered, not over-engineered.
- Handle more edge cases, not fewer; thoughtfulness > speed.
- Bias toward explicit over clever.
- Flag over-engineering: if a proposed abstraction only serves the
  current use case with no evidence of future reuse, call it out.
- Before proposing any new pattern, utility, or abstraction, search
  the existing codebase for prior art. If something similar exists,
  explain why reuse doesn't work before creating new.

## Pipeline workflow
When running /pipeline, /quality-gate, or /doc-sync commands:
- Execute phases autonomously. Do NOT pause for interactive input
  between phases.
- Stop and ask for human input ONLY at gate failures after 3 retries,
  or when the story-analyzer identifies open questions in Phase 0.
- Plan mode rules below do NOT apply during pipeline execution.

---

# Plan mode rules (only when reviewing plans, NOT during /pipeline)

Activate these rules when I ask you to review a plan, design, or
architecture — or when I'm working interactively outside the pipeline.

BEFORE YOU START:
Ask if I want one of two options:
1/ BIG CHANGE: Work through this interactively, one section at a time (Architecture → Code Quality → Tests → Performance) with at most 4 top issues in each section.
2/ SMALL CHANGE: Work through interactively ONE question per review section
FOR EACH STAGE OF REVIEW: output the explanation and pros and cons of each stage's questions AND your opinionated recommendation and why, and then use AskUserQuestion. Also NUMBER issues and then give LETTERS for options and when using AskUserQuestion make sure each option clearly labels the issue NUMBER and option LETTER so the user doesn't get confused. Make the recommended option always the 1st option.
