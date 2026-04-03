import type {
  SkillsResponse,
  RoleSummary,
  RoleDetail,
  ProficiencyScore,
} from "@/lib/types";
import type {
  AssessmentStartResponse,
  AssessmentReportResponse,
} from "@/lib/api";

// ── Skills ──────────────────────────────────────────────────────────

export const DEMO_SKILLS: SkillsResponse = {
  skills: [
    {
      id: "react",
      name: "React",
      category: "Frontend Frameworks",
      icon: "atom",
      description: "Component-based UI library",
      subSkills: ["Hooks", "Context API", "Suspense", "Server Components"],
    },
    {
      id: "typescript",
      name: "TypeScript",
      category: "Languages",
      icon: "file-code",
      description: "Typed superset of JavaScript",
      subSkills: ["Generics", "Type Guards", "Utility Types", "Declaration Files"],
    },
    {
      id: "css",
      name: "CSS",
      category: "Frontend Fundamentals",
      icon: "paintbrush",
      description: "Styling and layout for the web",
      subSkills: ["Flexbox", "Grid", "Animations", "Custom Properties"],
    },
    {
      id: "nextjs",
      name: "Next.js",
      category: "Frontend Frameworks",
      icon: "layout",
      description: "React meta-framework for production",
      subSkills: ["App Router", "Server Actions", "Middleware", "ISR"],
    },
    {
      id: "testing",
      name: "Testing",
      category: "Engineering Practices",
      icon: "test-tube",
      description: "Automated testing practices",
      subSkills: ["Unit Testing", "Integration Testing", "E2E Testing", "TDD"],
    },
  ],
  categories: ["Frontend Frameworks", "Languages", "Frontend Fundamentals", "Engineering Practices"],
};

// ── Roles ───────────────────────────────────────────────────────────

export const DEMO_ROLES: RoleSummary[] = [
  {
    id: "frontend_engineering",
    name: "Frontend Engineer",
    description: "Build user interfaces with modern web technologies",
    skillCount: 5,
    levels: ["junior", "mid", "senior"],
  },
];

export const DEMO_ROLE_DETAIL: RoleDetail = {
  id: "frontend_engineering",
  name: "Frontend Engineer",
  description: "Build user interfaces with modern web technologies",
  mappedSkillIds: ["react", "typescript", "css", "nextjs", "testing"],
  levels: [
    { name: "junior", conceptCount: 15 },
    { name: "mid", conceptCount: 30 },
    { name: "senior", conceptCount: 50 },
  ],
};

// ── Assessment Script ───────────────────────────────────────────────

export interface DemoQuestion {
  question: string;
  meta: {
    type: "assessment";
    topics_evaluated?: number;
    total_questions?: number;
    max_questions?: number;
  };
}

export const DEMO_QUESTIONS: DemoQuestion[] = [
  {
    question:
      "Let's start with the assessment. Explain how TypeScript generics work with constraints. Can you give an example of a generic function that accepts only objects with a specific property?",
    meta: {
      type: "assessment",
      topics_evaluated: 1,
      total_questions: 1,
      max_questions: 8,
    },
  },
  {
    question:
      "Tell me about the CSS Box Model. What's the difference between `content-box` and `border-box` for `box-sizing`? How does this affect layout calculations?",
    meta: {
      type: "assessment",
      topics_evaluated: 2,
      total_questions: 2,
      max_questions: 8,
    },
  },
  {
    question:
      "In Next.js App Router, what's the difference between Server Components and Client Components? When would you use `\"use client\"` and what are the tradeoffs?",
    meta: {
      type: "assessment",
      topics_evaluated: 3,
      total_questions: 3,
      max_questions: 8,
    },
  },
  {
    question:
      "How do you approach testing a React component that fetches data and renders a list? Walk me through the tools, patterns, and assertions you'd use.",
    meta: {
      type: "assessment",
      topics_evaluated: 4,
      total_questions: 4,
      max_questions: 8,
    },
  },
  {
    question:
      "Final question: You notice a React component rendering a list of 1,000+ items is causing jank. How would you debug and fix the performance issue? What tools and techniques would you reach for?",
    meta: {
      type: "assessment",
      topics_evaluated: 5,
      total_questions: 5,
      max_questions: 8,
    },
  },
];

// ── Demo Responses (what the "AI" says after each user answer) ──────

export const DEMO_RESPONSES: string[] = [
  "Good grasp of generics with constraints. Your example with `extends` was clear and practical. The `keyof` usage shows you understand the type system well.",
  "Nice explanation of the box model. Understanding `border-box` vs `content-box` is fundamental, and you explained it clearly with practical implications.",
  "Good comparison of Server and Client Components. You identified the key tradeoffs around bundle size, interactivity, and data fetching patterns.",
  "Thoughtful testing approach. Using React Testing Library with `findBy` queries for async content and mocking the API layer shows good testing instincts.",
  "Excellent debugging methodology! You mentioned React DevTools Profiler, virtualization with `react-window`, `useMemo`, and `React.memo` — all the right tools for the job.",
];

// ── Assessment Start ────────────────────────────────────────────────

export const DEMO_ASSESSMENT_START: AssessmentStartResponse = {
  sessionId: "demo-session-001",
  question: DEMO_QUESTIONS[0].question,
};

// ── Proficiency Scores ──────────────────────────────────────────────

export const DEMO_PROFICIENCY_SCORES: ProficiencyScore[] = [
  {
    skillId: "react",
    skillName: "React",
    score: 72,
    confidence: 0.85,
    reasoning:
      "Strong understanding of hooks, reconciliation, and rendering optimization. Some gaps in advanced patterns like Suspense boundaries.",
  },
  {
    skillId: "typescript",
    skillName: "TypeScript",
    score: 65,
    confidence: 0.8,
    reasoning:
      "Good grasp of generics and constraints. Could improve on advanced utility types and conditional types.",
  },
  {
    skillId: "css",
    skillName: "CSS",
    score: 80,
    confidence: 0.9,
    reasoning:
      "Solid understanding of the box model, flexbox, and layout. Clear and practical knowledge of common patterns.",
  },
  {
    skillId: "nextjs",
    skillName: "Next.js",
    score: 55,
    confidence: 0.75,
    reasoning:
      "Understands Server vs Client Components at a conceptual level but lacks depth in App Router patterns like parallel routes and intercepting routes.",
  },
  {
    skillId: "testing",
    skillName: "Testing",
    score: 48,
    confidence: 0.7,
    reasoning:
      "Knows React Testing Library basics but would benefit from deeper experience with integration testing, mocking strategies, and test architecture.",
  },
];

// ── Export Markdown ─────────────────────────────────────────────────

export const DEMO_EXPORT_MARKDOWN = `# Assessment Report

**Session:** \`demo-session-001\`
**Date:** 2026-03-16
**Target Level:** mid

---

## Proficiency Scores

| Skill | Score | Confidence | Bloom Level |
|-------|-------|------------|-------------|
| React | 72% | 85% | apply |
| TypeScript | 65% | 80% | apply |
| CSS | 80% | 90% | understand |
| Next.js | 55% | 75% | remember |
| Testing | 48% | 70% | apply |

---

## Knowledge Gaps

### 1. Next.js App Router
- **Current Confidence:** 60%
- **Target Bloom Level:** apply
- **Prerequisites:** React Hooks

### 2. Component Testing
- **Current Confidence:** 50%
- **Target Bloom Level:** analyze
- **Prerequisites:** React Hooks

### 3. CSS Modern Layout
- **Current Confidence:** 65%
- **Target Bloom Level:** apply
- **Prerequisites:** CSS Box Model

---

## Learning Plan

> Focus on deepening Next.js App Router knowledge, building stronger testing practices, and modernizing CSS skills.

**Total estimated time:** 48 hours

### Phase 1: Next.js Deep Dive (16h)

Biggest gap relative to target level

**Concepts:** App Router, Server Actions, Parallel Routes

### Phase 2: Testing Mastery (14h)

Second largest gap, builds on React fundamentals

**Concepts:** Integration Testing, Mock Strategies, Test Architecture

### Phase 3: TypeScript Advanced Patterns (10h)

Refinement of existing knowledge

**Concepts:** Conditional Types, Template Literal Types, Type-Level Programming

### Phase 4: CSS Modern Techniques (8h)

Round out strong CSS fundamentals with modern layout and animation patterns

**Concepts:** Container Queries, CSS Layers, Scroll-Driven Animations

---

*Generated by OpenLearning*
`;

// ── Gap Analysis ────────────────────────────────────────────────────

export const DEMO_GAP_ANALYSIS: AssessmentReportResponse["gapAnalysis"] = {
  overallReadiness: 64,
  summary:
    "You have strong React and CSS fundamentals, with room to grow in modern CSS techniques. Key growth areas are Next.js App Router patterns, testing depth, and advanced TypeScript. A focused 8-week plan can close the gaps.",
  gaps: [
    {
      skillId: "nextjs",
      skillName: "Next.js",
      currentLevel: 55,
      targetLevel: 75,
      gap: 20,
      priority: "critical",
      recommendation:
        "Deep-dive into App Router: parallel routes, intercepting routes, and server actions. Build a project using these patterns.",
    },
    {
      skillId: "testing",
      skillName: "Testing",
      currentLevel: 48,
      targetLevel: 70,
      gap: 22,
      priority: "high",
      recommendation:
        "Practice integration testing with Vitest and React Testing Library. Focus on testing async flows and error states.",
    },
    {
      skillId: "typescript",
      skillName: "TypeScript",
      currentLevel: 65,
      targetLevel: 80,
      gap: 15,
      priority: "medium",
      recommendation:
        "Study advanced utility types, conditional types, and template literal types. Work through type challenges.",
    },
    {
      skillId: "react",
      skillName: "React",
      currentLevel: 72,
      targetLevel: 80,
      gap: 8,
      priority: "low",
      recommendation:
        "Explore Suspense boundaries, transitions, and concurrent rendering patterns to round out your React knowledge.",
    },
    {
      skillId: "css",
      skillName: "CSS",
      currentLevel: 80,
      targetLevel: 90,
      gap: 10,
      priority: "low",
      recommendation:
        "Deepen knowledge of modern layout techniques like container queries, CSS layers (@layer), and advanced animation with scroll-driven animations.",
    },
  ],
};

// ── Learning Plan ───────────────────────────────────────────────────

export const DEMO_LEARNING_PLAN: AssessmentReportResponse["learningPlan"] = {
  summary:
    "An 8-week learning plan covering your key gaps: Next.js App Router, Testing practices, advanced TypeScript patterns, and modern CSS techniques.",
  totalHours: 65,
  phases: [
    {
      phaseNumber: 1,
      title: "Next.js Deep Dive",
      concepts: ["App Router", "Server Actions", "Parallel Routes", "Data Fetching"],
      rationale:
        "Master the App Router, including server components, parallel routes, and server actions.",
      resources: [
        { type: "article", title: "Next.js Documentation — Routing", url: null },
        { type: "article", title: "Next.js Caching Docs", url: null },
        { type: "project", title: "Server Actions Lab", url: null },
      ],
      estimatedHours: 14,
    },
    {
      phaseNumber: 2,
      title: "Testing Mastery",
      concepts: ["Integration Testing", "Mock Strategies", "E2E Testing", "Test Architecture"],
      rationale:
        "Build confidence in integration testing, mocking strategies, and test-driven development.",
      resources: [
        { type: "article", title: "Testing Library Docs", url: null },
        { type: "article", title: "MSW Documentation", url: null },
        { type: "article", title: "Playwright Documentation", url: null },
      ],
      estimatedHours: 16,
    },
    {
      phaseNumber: 3,
      title: "Advanced TypeScript",
      concepts: ["Conditional Types", "Template Literal Types", "Type-Level Programming"],
      rationale:
        "Level up your TypeScript skills with generics, conditional types, and type-level programming.",
      resources: [
        { type: "video", title: "Total TypeScript — Advanced Patterns", url: null },
        { type: "exercise", title: "Type Challenges Repository", url: null },
      ],
      estimatedHours: 12,
    },
    {
      phaseNumber: 4,
      title: "CSS Modern Techniques",
      concepts: ["Container Queries", "CSS Layers", "Scroll-Driven Animations"],
      rationale:
        "Deepen your CSS skills with container queries, CSS layers, and scroll-driven animations.",
      resources: [
        { type: "article", title: "MDN Container Queries", url: null },
        { type: "article", title: "MDN Scroll-Driven Animations", url: null },
      ],
      estimatedHours: 9,
    },
  ],
};

// ── Assessment Report ───────────────────────────────────────────────

export const DEMO_ASSESSMENT_REPORT: AssessmentReportResponse = {
  knowledgeGraph: {
    nodes: [
      { concept: "React Hooks", confidence: 0.85, bloomLevel: "Apply", prerequisites: [] },
      { concept: "React Reconciliation", confidence: 0.75, bloomLevel: "Analyze", prerequisites: ["React Hooks"] },
      { concept: "TypeScript Generics", confidence: 0.7, bloomLevel: "Apply", prerequisites: [] },
      { concept: "CSS Box Model", confidence: 0.9, bloomLevel: "Understand", prerequisites: [] },
      { concept: "CSS Flexbox & Grid", confidence: 0.85, bloomLevel: "Apply", prerequisites: ["CSS Box Model"] },
      { concept: "Next.js App Router", confidence: 0.6, bloomLevel: "Remember", prerequisites: ["React Hooks"] },
      { concept: "Component Testing", confidence: 0.5, bloomLevel: "Apply", prerequisites: ["React Hooks"] },
    ],
  },
  gapAnalysis: DEMO_GAP_ANALYSIS,
  learningPlan: DEMO_LEARNING_PLAN,
  proficiencyScores: DEMO_PROFICIENCY_SCORES,
};
