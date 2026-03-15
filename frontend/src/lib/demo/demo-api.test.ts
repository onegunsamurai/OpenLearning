import { useAppStore } from "@/lib/store";
import { demoApi } from "./demo-api";
import {
  DEMO_SKILLS,
  DEMO_ROLES,
  DEMO_ROLE_DETAIL,
  DEMO_JD_PARSE,
  DEMO_GAP_ANALYSIS,
  DEMO_LEARNING_PLAN,
  DEMO_ASSESSMENT_START,
  DEMO_ASSESSMENT_REPORT,
  DEMO_QUESTIONS,
  DEMO_RESPONSES,
} from "./fixtures";

beforeEach(() => {
  useAppStore.getState().reset();
});

describe("demoApi", () => {
  describe("getRoles", () => {
    it("returns demo roles", async () => {
      const result = await demoApi.getRoles();
      expect(result).toEqual(DEMO_ROLES);
    });
  });

  describe("getRole", () => {
    it("returns demo role detail", async () => {
      const result = await demoApi.getRole("frontend_engineering");
      expect(result).toEqual(DEMO_ROLE_DETAIL);
    });
  });

  describe("getSkills", () => {
    it("returns demo skills", async () => {
      const result = await demoApi.getSkills();
      expect(result).toEqual(DEMO_SKILLS);
    });
  });

  describe("parseJD", () => {
    it("returns demo JD parse result", async () => {
      const result = await demoApi.parseJD("any job description");
      expect(result).toEqual(DEMO_JD_PARSE);
    });
  });

  describe("gapAnalysis", () => {
    it("returns demo gap analysis", async () => {
      const result = await demoApi.gapAnalysis([]);
      expect(result).toEqual(DEMO_GAP_ANALYSIS);
    });
  });

  describe("learningPlan", () => {
    it("returns demo learning plan", async () => {
      const result = await demoApi.learningPlan({
        overallReadiness: 0,
        summary: "",
        gaps: [],
      });
      expect(result).toEqual(DEMO_LEARNING_PLAN);
    });
  });

  describe("assessmentStart", () => {
    it("returns demo assessment start response", async () => {
      const result = await demoApi.assessmentStart(["react"]);
      expect(result).toEqual(DEMO_ASSESSMENT_START);
    });

    it("resets demo step counter", async () => {
      useAppStore.getState().advanceDemoStep();
      useAppStore.getState().advanceDemoStep();
      expect(useAppStore.getState().demoStep).toBe(2);

      await demoApi.assessmentStart(["react"]);
      expect(useAppStore.getState().demoStep).toBe(0);
    });
  });

  describe("assessmentRespond", () => {
    it("returns a Response with SSE body", async () => {
      const response = await demoApi.assessmentRespond("demo-session", "my answer");
      expect(response).toBeInstanceOf(Response);
      expect(response.headers.get("Content-Type")).toBe("text/event-stream");
    });

    it("advances demo step on each call", async () => {
      expect(useAppStore.getState().demoStep).toBe(0);
      await demoApi.assessmentRespond("s", "a");
      expect(useAppStore.getState().demoStep).toBe(1);
      await demoApi.assessmentRespond("s", "a");
      expect(useAppStore.getState().demoStep).toBe(2);
    });
  });

  describe("assessmentReport", () => {
    it("returns demo assessment report", async () => {
      const result = await demoApi.assessmentReport("demo-session");
      expect(result).toEqual(DEMO_ASSESSMENT_REPORT);
    });
  });
});

describe("SSE stream content", () => {
  async function readStream(response: Response): Promise<string[]> {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    const lines: string[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      for (const line of chunk.split("\n")) {
        if (line.startsWith("data: ")) {
          lines.push(line.slice(6));
        }
      }
    }
    return lines;
  }

  it("emits response text words followed by META and next question", async () => {
    useAppStore.getState().resetDemoStep();
    const response = await demoApi.assessmentRespond("s", "answer");
    const lines = await readStream(response);

    // Should contain response words
    const responseWords = DEMO_RESPONSES[0].split(" ");
    expect(lines[0]).toBe(responseWords[0]);

    // Should contain a META line
    const metaLine = lines.find((l) => l.startsWith("[META]"));
    expect(metaLine).toBeDefined();

    // Should end with [DONE]
    expect(lines[lines.length - 1]).toBe("[DONE]");

    // Should NOT contain [ASSESSMENT_COMPLETE] for step 0
    expect(lines.find((l) => l === "[ASSESSMENT_COMPLETE]")).toBeUndefined();
  });

  it("emits [ASSESSMENT_COMPLETE] on final question", async () => {
    // Advance to the last question
    for (let i = 0; i < DEMO_QUESTIONS.length - 1; i++) {
      useAppStore.getState().advanceDemoStep();
    }

    const response = await demoApi.assessmentRespond("s", "final answer");
    const lines = await readStream(response);

    expect(lines).toContain("[ASSESSMENT_COMPLETE]");
    expect(lines[lines.length - 1]).toBe("[DONE]");
  });
});
