import type {
  SkillsResponse,
  RoleSummary,
  RoleDetail,
  GapAnalysis,
  LearningPlan,
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
  questionType: string;
  meta: {
    type: "calibration" | "assessment";
    step: number;
    total_steps: number;
    topics_evaluated?: number;
    total_questions?: number;
    max_questions?: number;
  };
}

export const DEMO_QUESTIONS: DemoQuestion[] = [
  // Calibration (3 questions)
  {
    question:
      "Let's start with a warm-up question. Can you explain the difference between `let`, `const`, and `var` in JavaScript? When would you choose one over the other?",
    questionType: "open",
    meta: { type: "calibration", step: 1, total_steps: 3 },
  },
  {
    question:
      "Good answer! Now, how would you implement a custom React hook for form validation? Walk me through the key design decisions you'd make.",
    questionType: "open",
    meta: { type: "calibration", step: 2, total_steps: 3 },
  },
  {
    question:
      "Nice. For the last calibration question: Can you describe React's reconciliation algorithm? How does React decide what to re-render, and what techniques can you use to optimize rendering performance?",
    questionType: "open",
    meta: { type: "calibration", step: 3, total_steps: 3 },
  },
  // Assessment (5 questions)
  {
    question:
      "Let's move into the assessment. Explain how TypeScript generics work with constraints. Can you give an example of a generic function that accepts only objects with a specific property?",
    questionType: "open",
    meta: {
      type: "assessment",
      step: 1,
      total_steps: 5,
      topics_evaluated: 1,
      total_questions: 4,
      max_questions: 8,
    },
  },
  {
    question:
      "Tell me about the CSS Box Model. What's the difference between `content-box` and `border-box` for `box-sizing`? How does this affect layout calculations?",
    questionType: "open",
    meta: {
      type: "assessment",
      step: 2,
      total_steps: 5,
      topics_evaluated: 2,
      total_questions: 5,
      max_questions: 8,
    },
  },
  {
    question:
      "In Next.js App Router, what's the difference between Server Components and Client Components? When would you use `\"use client\"` and what are the tradeoffs?",
    questionType: "open",
    meta: {
      type: "assessment",
      step: 3,
      total_steps: 5,
      topics_evaluated: 3,
      total_questions: 6,
      max_questions: 8,
    },
  },
  {
    question:
      "How do you approach testing a React component that fetches data and renders a list? Walk me through the tools, patterns, and assertions you'd use.",
    questionType: "open",
    meta: {
      type: "assessment",
      step: 4,
      total_steps: 5,
      topics_evaluated: 4,
      total_questions: 7,
      max_questions: 8,
    },
  },
  {
    question:
      "Final question: You notice a React component rendering a list of 1,000+ items is causing jank. How would you debug and fix the performance issue? What tools and techniques would you reach for?",
    questionType: "open",
    meta: {
      type: "assessment",
      step: 5,
      total_steps: 5,
      topics_evaluated: 5,
      total_questions: 8,
      max_questions: 8,
    },
  },
];

// ── Demo Responses (what the "AI" says after each user answer) ──────

export const DEMO_RESPONSES: string[] = [
  "Great explanation of variable scoping! You clearly understand the temporal dead zone and block scoping differences. Let me move on to something a bit more involved.",
  "Solid approach to the custom hook design. I like that you considered validation schemas and debouncing. Let's see how you handle a trickier topic.",
  "Excellent breakdown of the reconciliation algorithm. You touched on the fiber architecture and key-based diffing, which shows strong fundamentals. Let's move into the full assessment now.",
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
  questionType: DEMO_QUESTIONS[0].questionType,
  step: 1,
  totalSteps: 3,
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
  gapNodes: [
    { concept: "Next.js App Router", currentConfidence: 0.6, targetBloomLevel: "Apply", prerequisites: ["React Hooks"] },
    { concept: "Component Testing", currentConfidence: 0.5, targetBloomLevel: "Analyze", prerequisites: ["React Hooks"] },
    { concept: "TypeScript Advanced Types", currentConfidence: 0.45, targetBloomLevel: "Apply", prerequisites: ["TypeScript Generics"] },
    { concept: "CSS Modern Layout", currentConfidence: 0.65, targetBloomLevel: "Apply", prerequisites: ["CSS Box Model"] },
  ],
  learningPlan: {
    summary: "Focus on deepening Next.js App Router knowledge, building stronger testing practices, and modernizing CSS skills.",
    totalHours: 48,
    phases: [
      {
        phaseNumber: 1,
        title: "Next.js Deep Dive",
        concepts: ["App Router", "Server Actions", "Parallel Routes"],
        rationale: "Biggest gap relative to target level",
        resources: [
          { type: "documentation", title: "Next.js App Router Docs", url: null },
          { type: "tutorial", title: "Building with App Router", url: null },
        ],
        estimatedHours: 16,
      },
      {
        phaseNumber: 2,
        title: "Testing Mastery",
        concepts: ["Integration Testing", "Mock Strategies", "Test Architecture"],
        rationale: "Second largest gap, builds on React fundamentals",
        resources: [
          { type: "course", title: "Testing JavaScript Applications", url: null },
          { type: "documentation", title: "Vitest + RTL Guide", url: null },
        ],
        estimatedHours: 14,
      },
      {
        phaseNumber: 3,
        title: "TypeScript Advanced Patterns",
        concepts: ["Conditional Types", "Template Literal Types", "Type-Level Programming"],
        rationale: "Refinement of existing knowledge",
        resources: [
          { type: "course", title: "Total TypeScript", url: null },
        ],
        estimatedHours: 10,
      },
      {
        phaseNumber: 4,
        title: "CSS Modern Techniques",
        concepts: ["Container Queries", "CSS Layers", "Scroll-Driven Animations"],
        rationale: "Round out strong CSS fundamentals with modern layout and animation patterns",
        resources: [
          { type: "documentation", title: "MDN CSS Reference", url: null },
        ],
        estimatedHours: 8,
      },
    ],
  },
  proficiencyScores: DEMO_PROFICIENCY_SCORES,
};

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

export const DEMO_GAP_ANALYSIS: GapAnalysis = {
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

export const DEMO_LEARNING_PLAN: LearningPlan = {
  title: "Frontend Engineer Growth Plan",
  summary:
    "An 8-week learning plan covering your key gaps: Next.js App Router, Testing practices, advanced TypeScript patterns, and modern CSS techniques.",
  totalHours: 65,
  totalWeeks: 8,
  phases: [
    {
      phase: 1,
      name: "Next.js Deep Dive",
      description:
        "Master the App Router, including server components, parallel routes, and server actions.",
      modules: [
        {
          id: "mod-1",
          title: "App Router Fundamentals",
          description: "Learn the mental model of the Next.js App Router and its file conventions.",
          type: "theory",
          phase: 1,
          skillIds: ["nextjs"],
          durationHours: 4,
          objectives: [
            "Understand layout nesting and loading states",
            "Implement parallel and intercepting routes",
          ],
          resources: ["Next.js Documentation — Routing"],
        },
        {
          id: "mod-1b",
          title: "Data Fetching & Caching Strategies",
          description: "Understand fetch caching, revalidation, and ISR in the App Router.",
          type: "theory",
          phase: 1,
          skillIds: ["nextjs"],
          durationHours: 3,
          objectives: [
            "Understand fetch caching, revalidation, and ISR strategies",
            "Implement on-demand revalidation with revalidateTag",
          ],
          resources: ["Next.js Caching Docs"],
        },
        {
          id: "mod-2",
          title: "Server Actions Lab",
          description: "Build a form-heavy feature using Server Actions and revalidation.",
          type: "lab",
          phase: 1,
          skillIds: ["nextjs", "react"],
          durationHours: 6,
          objectives: [
            "Implement form mutations with server actions",
            "Handle optimistic updates",
          ],
          resources: ["Next.js Server Actions Guide"],
        },
        {
          id: "mod-3",
          title: "App Router Quiz",
          description: "Test your understanding of App Router concepts.",
          type: "quiz",
          phase: 1,
          skillIds: ["nextjs"],
          durationHours: 1,
          objectives: ["Score 80%+ on routing concepts"],
          resources: [],
        },
      ],
    },
    {
      phase: 2,
      name: "Testing Mastery",
      description:
        "Build confidence in integration testing, mocking strategies, and test-driven development.",
      modules: [
        {
          id: "mod-4",
          title: "Integration Testing Patterns",
          description: "Learn to test components with data fetching, routing, and state.",
          type: "theory",
          phase: 2,
          skillIds: ["testing", "react"],
          durationHours: 4,
          objectives: [
            "Test async data flows with MSW",
            "Write meaningful assertions for user interactions",
          ],
          resources: ["Testing Library Docs", "MSW Documentation"],
        },
        {
          id: "mod-4b",
          title: "E2E Testing with Playwright",
          description: "Learn cross-browser end-to-end testing with Playwright.",
          type: "theory",
          phase: 2,
          skillIds: ["testing"],
          durationHours: 3,
          objectives: [
            "Write cross-browser E2E tests",
            "Test user flows with page object model",
          ],
          resources: ["Playwright Documentation", "Testing Library Docs"],
        },
        {
          id: "mod-5",
          title: "Test a Real Feature",
          description: "Write a full test suite for an existing component in your project.",
          type: "lab",
          phase: 2,
          skillIds: ["testing"],
          durationHours: 8,
          objectives: [
            "Achieve 90%+ coverage on a feature module",
            "Test error states and loading states",
          ],
          resources: [],
        },
        {
          id: "mod-5b",
          title: "Testing Quiz",
          description: "Verify your understanding of testing patterns and strategies.",
          type: "quiz",
          phase: 2,
          skillIds: ["testing"],
          durationHours: 1,
          objectives: ["Score 80%+ on testing patterns and strategies"],
          resources: [],
        },
      ],
    },
    {
      phase: 3,
      name: "Advanced TypeScript",
      description:
        "Level up your TypeScript skills with generics, conditional types, and type-level programming.",
      modules: [
        {
          id: "mod-6",
          title: "Advanced Type Patterns",
          description: "Master conditional types, mapped types, and template literal types.",
          type: "theory",
          phase: 3,
          skillIds: ["typescript"],
          durationHours: 5,
          objectives: [
            "Implement custom utility types",
            "Use conditional types for API type safety",
          ],
          resources: ["Total TypeScript — Advanced Patterns", "TypeScript Handbook — Advanced Types"],
        },
        {
          id: "mod-7",
          title: "Type Challenges",
          description: "Work through progressive type challenges to solidify your skills.",
          type: "lab",
          phase: 3,
          skillIds: ["typescript"],
          durationHours: 6,
          objectives: [
            "Complete 20+ type challenges at medium difficulty",
            "Build a type-safe event emitter",
          ],
          resources: ["Type Challenges Repository", "type-challenges/type-challenges on GitHub"],
        },
        {
          id: "mod-8",
          title: "TypeScript Assessment",
          description: "Verify your advanced TypeScript knowledge.",
          type: "quiz",
          phase: 3,
          skillIds: ["typescript"],
          durationHours: 1,
          objectives: ["Score 80%+ on advanced type concepts"],
          resources: [],
        },
      ],
    },
    {
      phase: 4,
      name: "CSS Modern Techniques",
      description:
        "Deepen your CSS skills with container queries, CSS layers, and scroll-driven animations.",
      modules: [
        {
          id: "mod-9",
          title: "Modern Layout Patterns",
          description: "Learn container queries and CSS layers for component-scoped styling.",
          type: "theory",
          phase: 4,
          skillIds: ["css"],
          durationHours: 3,
          objectives: [
            "Use container queries for component-scoped responsive design",
            "Organize styles with CSS layers (@layer)",
          ],
          resources: ["MDN Container Queries", "web.dev CSS Layers Guide"],
        },
        {
          id: "mod-10",
          title: "Advanced Animations Lab",
          description: "Build scroll-driven animations and a micro-interaction library.",
          type: "lab",
          phase: 4,
          skillIds: ["css"],
          durationHours: 5,
          objectives: [
            "Implement scroll-driven animations",
            "Build a micro-interaction library with CSS transitions",
          ],
          resources: ["MDN Scroll-Driven Animations"],
        },
        {
          id: "mod-11",
          title: "CSS Assessment",
          description: "Verify your knowledge of modern CSS techniques.",
          type: "quiz",
          phase: 4,
          skillIds: ["css"],
          durationHours: 1,
          objectives: ["Score 80%+ on modern CSS techniques"],
          resources: [],
        },
      ],
    },
  ],
};
