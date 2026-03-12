import { useAppStore } from "./store";

// Reset store between tests
beforeEach(() => {
  useAppStore.getState().reset();
  sessionStorage.clear();
});

describe("useAppStore", () => {
  describe("initial state", () => {
    it("has correct defaults", () => {
      const state = useAppStore.getState();
      expect(state.currentStep).toBe(0);
      expect(state.selectedSkillIds).toEqual([]);
      expect(state.jobDescription).toBe("");
      expect(state.assessmentSessionId).toBeNull();
      expect(state.messages).toEqual([]);
      expect(state.proficiencyScores).toEqual([]);
      expect(state.gapAnalysis).toBeNull();
      expect(state.learningPlan).toBeNull();
    });
  });

  describe("setCurrentStep", () => {
    it("updates step", () => {
      useAppStore.getState().setCurrentStep(3);
      expect(useAppStore.getState().currentStep).toBe(3);
    });
  });

  describe("setJobDescription", () => {
    it("updates job description", () => {
      useAppStore.getState().setJobDescription("Senior React Developer");
      expect(useAppStore.getState().jobDescription).toBe(
        "Senior React Developer"
      );
    });
  });

  describe("setSelectedSkillIds", () => {
    it("replaces skill IDs", () => {
      useAppStore.getState().setSelectedSkillIds(["a", "b"]);
      expect(useAppStore.getState().selectedSkillIds).toEqual(["a", "b"]);
    });
  });

  describe("toggleSkill", () => {
    it("adds a skill when not present", () => {
      useAppStore.getState().toggleSkill("s1");
      expect(useAppStore.getState().selectedSkillIds).toEqual(["s1"]);
    });

    it("removes a skill when already present", () => {
      useAppStore.getState().setSelectedSkillIds(["s1", "s2"]);
      useAppStore.getState().toggleSkill("s1");
      expect(useAppStore.getState().selectedSkillIds).toEqual(["s2"]);
    });

    it("handles multiple toggles correctly", () => {
      useAppStore.getState().toggleSkill("a");
      useAppStore.getState().toggleSkill("b");
      useAppStore.getState().toggleSkill("a");
      expect(useAppStore.getState().selectedSkillIds).toEqual(["b"]);
    });
  });

  describe("setAssessmentSessionId", () => {
    it("updates assessment session ID", () => {
      useAppStore.getState().setAssessmentSessionId("sess-42");
      expect(useAppStore.getState().assessmentSessionId).toBe("sess-42");
    });
  });

  describe("addMessage", () => {
    it("appends a message", () => {
      const msg = { role: "user" as const, content: "hello" };
      useAppStore.getState().addMessage(msg);
      expect(useAppStore.getState().messages).toEqual([msg]);
    });

    it("preserves order with multiple appends", () => {
      const m1 = { role: "user" as const, content: "first" };
      const m2 = { role: "assistant" as const, content: "second" };
      const m3 = { role: "user" as const, content: "third" };
      useAppStore.getState().addMessage(m1);
      useAppStore.getState().addMessage(m2);
      useAppStore.getState().addMessage(m3);
      expect(useAppStore.getState().messages).toEqual([m1, m2, m3]);
    });
  });

  describe("setMessages", () => {
    it("replaces messages", () => {
      useAppStore.getState().addMessage({ role: "user", content: "old" });
      const newMsgs = [{ role: "assistant" as const, content: "new" }];
      useAppStore.getState().setMessages(newMsgs);
      expect(useAppStore.getState().messages).toEqual(newMsgs);
    });
  });

  describe("setProficiencyScores", () => {
    it("sets scores", () => {
      const scores = [
        {
          skillId: "s1",
          skillName: "React",
          score: 80,
          confidence: 0.9,
          reasoning: "Good",
        },
      ];
      useAppStore.getState().setProficiencyScores(scores);
      expect(useAppStore.getState().proficiencyScores).toEqual(scores);
    });
  });

  describe("setGapAnalysis", () => {
    it("sets gap analysis", () => {
      const analysis = {
        overallReadiness: 75,
        summary: "On track",
        gaps: [],
      };
      useAppStore.getState().setGapAnalysis(analysis);
      expect(useAppStore.getState().gapAnalysis).toEqual(analysis);
    });
  });

  describe("setLearningPlan", () => {
    it("sets learning plan", () => {
      const plan = {
        title: "Plan",
        summary: "Learn",
        totalHours: 10,
        totalWeeks: 2,
        phases: [],
      };
      useAppStore.getState().setLearningPlan(plan);
      expect(useAppStore.getState().learningPlan).toEqual(plan);
    });
  });

  describe("reset", () => {
    it("restores all fields to initial values", () => {
      useAppStore.getState().setCurrentStep(5);
      useAppStore.getState().setJobDescription("JD");
      useAppStore.getState().setSelectedSkillIds(["x"]);
      useAppStore.getState().setAssessmentSessionId("sess-1");
      useAppStore
        .getState()
        .addMessage({ role: "user", content: "hi" });
      useAppStore.getState().setProficiencyScores([
        {
          skillId: "s1",
          skillName: "React",
          score: 80,
          confidence: 0.9,
          reasoning: "Good",
        },
      ]);
      useAppStore.getState().setGapAnalysis({
        overallReadiness: 50,
        summary: "s",
        gaps: [],
      });

      useAppStore.getState().reset();

      const state = useAppStore.getState();
      expect(state.currentStep).toBe(0);
      expect(state.selectedSkillIds).toEqual([]);
      expect(state.jobDescription).toBe("");
      expect(state.assessmentSessionId).toBeNull();
      expect(state.messages).toEqual([]);
      expect(state.proficiencyScores).toEqual([]);
      expect(state.gapAnalysis).toBeNull();
      expect(state.learningPlan).toBeNull();
    });
  });

  describe("sessionStorage persistence", () => {
    it("persists state to sessionStorage", () => {
      useAppStore.getState().setCurrentStep(2);
      // Zustand persist middleware writes synchronously on set
      const stored = sessionStorage.getItem("open-learning-store");
      expect(stored).not.toBeNull();
      const parsed = JSON.parse(stored!);
      expect(parsed.state.currentStep).toBe(2);
    });

    it("rehydrates from sessionStorage", () => {
      const payload = {
        state: {
          currentStep: 7,
          selectedSkillIds: ["rehydrated"],
          jobDescription: "test",
          assessmentSessionId: null,
          messages: [],
          proficiencyScores: [],
          gapAnalysis: null,
          learningPlan: null,
        },
        version: 0,
      };
      sessionStorage.setItem(
        "open-learning-store",
        JSON.stringify(payload)
      );

      // Trigger rehydration
      useAppStore.persist.rehydrate();

      expect(useAppStore.getState().currentStep).toBe(7);
      expect(useAppStore.getState().selectedSkillIds).toEqual([
        "rehydrated",
      ]);
    });
  });
});
