# ADR-144: Success State UI for Zero Skill Gaps

## Status
Proposed

## Context
When a user scores 100% on all assessed skills (`gaps.length === 0`), the gap-analysis and learning-plan pages render empty content areas. We need celebratory success states that guide the user toward next steps.

## Decisions

### D1: Success state trigger
**Condition:** `gapAnalysis.gaps.length === 0`
Deterministic structural indicator — we don't rely on `overallReadiness === 100` which is LLM-generated.

### D2: Extract `SkillScoreCard` from `AssessmentComplete.tsx`
**Location:** `frontend/src/components/shared/skill-score-card.tsx`
Inline card (lines 39-56 of AssessmentComplete) becomes standalone component with 3 consumers:
1. AssessmentComplete (existing)
2. NoGapsHero on gap-analysis page (new)
3. NoGapsSuccess on learning-plan page (new)

### D3: Gap-analysis success state — `NoGapsHero`
**Location:** `frontend/src/components/gap-analysis/no-gaps-hero.tsx`
When `gaps.length === 0`, replaces radar chart + gap cards with:
- GapSummary (reused as-is, shows readiness ring)
- SkillScoreCard list (from proficiencyScores)
- CTAs: "Try a Harder Level" (or "Add More Skills" at Staff) + "View Learning Plan"

### D4: Learning-plan success state — `NoGapsSuccess`
**Location:** `frontend/src/components/learning-plan/no-gaps-success.tsx`
When `phases.length === 0`, replaces PlanHeader + PlanTimeline with:
- Congratulations message
- SkillScoreCard list
- CTAs matching gap-analysis page

Separate component (not PlanHeader modification) because PlanHeader's stats are meaningless at zero phases.

### D5: Component hierarchy

```
gap-analysis/page.tsx
├── (gaps.length > 0) existing layout
└── (gaps.length === 0) NoGapsHero
    ├── GapSummary (readiness=100)
    ├── SkillScoreCard[]
    └── CTAs

learning-plan/page.tsx
├── (phases.length > 0) existing layout
└── (phases.length === 0) NoGapsSuccess
    ├── SkillScoreCard[]
    └── CTAs
```

### D6: Level constants extraction
**Location:** `frontend/src/lib/constants.ts`
Extract `LEVELS`, `LEVEL_LABELS`, `MAX_LEVEL` from `role-selector.tsx` to shared constants.

## CTA Logic

| targetLevel | Primary CTA | Action |
|---|---|---|
| `"staff"` (max) | "Add More Skills" | `reset()` + `router.push("/")` |
| Any other | "Try a Harder Level" | `reset()` + `router.push("/")` |

Secondary CTA is always "View Learning Plan" / "Start New Assessment".

## File Changes

### New Files
- `frontend/src/lib/constants.ts` — Shared level constants
- `frontend/src/components/shared/skill-score-card.tsx` — Extracted score card
- `frontend/src/components/gap-analysis/no-gaps-hero.tsx` — Gap analysis success state
- `frontend/src/components/learning-plan/no-gaps-success.tsx` — Learning plan success state
- Tests for each new file

### Modified Files
- `frontend/src/components/assessment/AssessmentComplete.tsx` — Use SkillScoreCard
- `frontend/src/components/onboarding/role-selector.tsx` — Import from constants
- `frontend/src/app/gap-analysis/page.tsx` — Add success state branch
- `frontend/src/app/learning-plan/page.tsx` — Add success state branch
- Page test files — Add success state tests

## Implementation Order
1. Constants extraction + SkillScoreCard extraction (foundations)
2. Gap-analysis NoGapsHero
3. Learning-plan NoGapsSuccess

## Risks
- **Store `targetLevel` stale/missing:** Treat unknown as non-max (safe default)
- **LLM returns `gaps: []` unexpectedly:** Trust backend; scores will still show actual values
