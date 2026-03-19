import { renderHook, act, waitFor } from "@testing-library/react";
import { vi } from "vitest";

// Mock the api module — use importOriginal to get the real ApiError class
vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>();
  return {
    ApiError: mod.ApiError,
    api: {
      assessmentStart: vi.fn(),
      assessmentRespond: vi.fn(),
      assessmentReport: vi.fn(),
    },
  };
});

import { useAssessmentChat } from "./useAssessmentChat";
import { api, ApiError } from "@/lib/api";

const mockedApi = vi.mocked(api);

/** Helper: build a mock Response with a ReadableStream from SSE chunks */
function createSSEResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });

  return {
    ok: true,
    status: 200,
    body: stream,
  } as unknown as Response;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useAssessmentChat", () => {
  const defaultOpts = { skillIds: ["s1", "s2"] };

  describe("initial state", () => {
    it("starts with empty messages, ready status, no error, no progress", () => {
      const { result } = renderHook(() => useAssessmentChat(defaultOpts));
      expect(result.current.messages).toEqual([]);
      expect(result.current.status).toBe("ready");
      expect(result.current.error).toBeNull();
      expect(result.current.progress).toBeNull();
    });
  });

  describe("initialiseChat", () => {
    it("transitions through statuses and sets first message", async () => {
      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "What is React?",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const { result } = renderHook(() => useAssessmentChat(defaultOpts));

      await act(() => result.current.initialiseChat());

      expect(result.current.status).toBe("ready");
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].role).toBe("assistant");
      expect(result.current.messages[0].content).toBe("What is React?");
    });

    it("sets initial progress", async () => {
      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "Q",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const { result } = renderHook(() => useAssessmentChat(defaultOpts));
      await act(() => result.current.initialiseChat());

      expect(result.current.progress).toEqual({
        type: "calibration",
        step: 1,
        totalSteps: 3,
      });
    });

    it("handles failure", async () => {
      mockedApi.assessmentStart.mockRejectedValueOnce(
        new Error("Network error")
      );

      const { result } = renderHook(() => useAssessmentChat(defaultOpts));
      await act(() => result.current.initialiseChat());

      expect(result.current.status).toBe("error");
      expect(result.current.error?.message).toBe("Network error");
    });

    it("handles non-Error throws", async () => {
      mockedApi.assessmentStart.mockRejectedValueOnce("string error");

      const { result } = renderHook(() => useAssessmentChat(defaultOpts));
      await act(() => result.current.initialiseChat());

      expect(result.current.status).toBe("error");
      expect(result.current.error?.message).toBe(
        "Failed to start assessment"
      );
    });

    it("clears previous messages when called again", async () => {
      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "Q1",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const { result } = renderHook(() => useAssessmentChat(defaultOpts));
      await act(() => result.current.initialiseChat());
      expect(result.current.messages).toHaveLength(1);

      // Call again — should start fresh
      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-2",
        question: "Q2",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });
      await act(() => result.current.initialiseChat());
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].content).toBe("Q2");
    });
  });

  describe("sendMessage", () => {
    it("sets error when no active session", async () => {
      const { result } = renderHook(() => useAssessmentChat(defaultOpts));

      await act(() => result.current.sendMessage("hello"));

      expect(result.current.error?.message).toBe("No active session");
    });

    it("adds user message with correct content", async () => {
      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "Q1",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const { result } = renderHook(() => useAssessmentChat(defaultOpts));
      await act(() => result.current.initialiseChat());

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse(["data: Reply\n"])
      );
      await act(() => result.current.sendMessage("my specific answer"));

      const userMsg = result.current.messages.find((m) => m.role === "user");
      expect(userMsg).toBeDefined();
      expect(userMsg!.content).toBe("my specific answer");
    });

    it("clears previous error on new message", async () => {
      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "Q1",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const { result } = renderHook(() => useAssessmentChat(defaultOpts));
      await act(() => result.current.initialiseChat());

      // Trigger an error
      mockedApi.assessmentRespond.mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response);
      await act(() => result.current.sendMessage("fail"));
      expect(result.current.error).not.toBeNull();

      // Send another message — error should clear
      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse(["data: OK\n"])
      );
      await act(() => result.current.sendMessage("retry"));
      expect(result.current.error).toBeNull();
    });
  });

  describe("SSE streaming", () => {
    async function setupWithSession() {
      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "Q1",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const hook = renderHook(() =>
        useAssessmentChat(defaultOpts)
      );
      await act(() => hook.result.current.initialiseChat());
      return hook;
    }

    it("accumulates text from SSE data lines", async () => {
      const { result } = await setupWithSession();

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([
          "data: Hello \n",
          "data: World\n",
        ])
      );

      await act(() => result.current.sendMessage("my answer"));

      // User message + assistant response
      expect(result.current.messages).toHaveLength(3);
      expect(result.current.messages[2].content).toBe("Hello World");
      expect(result.current.status).toBe("ready");
    });

    it("skips [DONE] tokens", async () => {
      const { result } = await setupWithSession();

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([
          "data: Hello\n",
          "data: [DONE]\n",
        ])
      );

      await act(() => result.current.sendMessage("answer"));

      expect(result.current.messages[2].content).toBe("Hello");
    });

    it("updates progress on [META] chunks", async () => {
      const { result } = await setupWithSession();

      const meta = JSON.stringify({
        type: "assessment",
        step: 2,
        total_steps: 5,
        topics_evaluated: 3,
        total_questions: 10,
        max_questions: 15,
      });

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([
          `data: [META]${meta}\n`,
          "data: Next question\n",
        ])
      );

      await act(() => result.current.sendMessage("answer"));

      expect(result.current.progress).toEqual({
        type: "assessment",
        step: 2,
        totalSteps: 5,
        topicsEvaluated: 3,
        totalQuestions: 10,
        maxQuestions: 15,
      });
    });

    it("ignores malformed [META] JSON", async () => {
      const { result } = await setupWithSession();

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([
          "data: [META]{bad json\n",
          "data: Content\n",
        ])
      );

      await act(() => result.current.sendMessage("answer"));

      // Should not crash, content should still accumulate
      expect(result.current.messages[2].content).toBe("Content");
    });

    it("triggers onAssessmentComplete callback on [ASSESSMENT_COMPLETE]", async () => {
      const onComplete = vi.fn();

      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "Q1",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const { result } = renderHook(() =>
        useAssessmentChat({
          ...defaultOpts,
          onAssessmentComplete: onComplete,
        })
      );

      await act(() => result.current.initialiseChat());

      const scores = [
        {
          skillId: "s1",
          skillName: "React",
          score: 80,
          confidence: 0.9,
          reasoning: "Good",
        },
      ];
      mockedApi.assessmentReport.mockResolvedValueOnce({
        proficiencyScores: scores,
        knowledgeGraph: { nodes: [] },
        gapNodes: [],
        learningPlan: { summary: "", totalHours: 0, phases: [] },
      });

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([
          "data: Done!\n",
          "data: [ASSESSMENT_COMPLETE]\n",
        ])
      );

      await act(() => result.current.sendMessage("final answer"));

      await waitFor(() => {
        expect(onComplete).toHaveBeenCalledWith(scores);
      });
    });

    it("handles report fetch failure gracefully", async () => {
      const onComplete = vi.fn();
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "Q1",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const { result } = renderHook(() =>
        useAssessmentChat({
          ...defaultOpts,
          onAssessmentComplete: onComplete,
        })
      );

      await act(() => result.current.initialiseChat());

      mockedApi.assessmentReport.mockRejectedValueOnce(
        new Error("Report failed")
      );

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse(["data: [ASSESSMENT_COMPLETE]\n"])
      );

      await act(() => result.current.sendMessage("answer"));

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          "Failed to fetch assessment report:",
          expect.any(Error)
        );
      });

      // Should not call onComplete
      expect(onComplete).not.toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it("skips markdown fence lines", async () => {
      const { result } = await setupWithSession();

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([
          "data: ```json\n",
          "data: content\n",
          "data: ```\n",
        ])
      );

      await act(() => result.current.sendMessage("answer"));

      expect(result.current.messages[2].content).toBe("content");
    });

    it("handles response not ok with ApiError", async () => {
      const { result } = await setupWithSession();

      mockedApi.assessmentRespond.mockResolvedValueOnce({
        ok: false,
        status: 401,
        headers: new Headers(),
        json: () =>
          Promise.resolve({
            detail: "Your API key is invalid or has been revoked.",
          }),
      } as unknown as Response);

      await act(() => result.current.sendMessage("answer"));

      expect(result.current.status).toBe("error");
      expect(result.current.error).toBeInstanceOf(ApiError);
      expect((result.current.error as InstanceType<typeof ApiError>).status).toBe(401);
    });

    it("parses [ERROR] SSE event with structured JSON", async () => {
      const { result } = await setupWithSession();

      const errorPayload = JSON.stringify({
        status: 429,
        detail: "Rate limit reached",
        retryAfter: "30",
      });

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([`data: [ERROR]${errorPayload}\n`])
      );

      await act(() => result.current.sendMessage("answer"));

      expect(result.current.status).toBe("error");
      expect(result.current.error).toBeInstanceOf(ApiError);
      expect((result.current.error as InstanceType<typeof ApiError>).status).toBe(429);
    });

    it("parses [ERROR] SSE event with auth error", async () => {
      const { result } = await setupWithSession();

      const errorPayload = JSON.stringify({
        status: 401,
        detail: "Your API key is invalid",
      });

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([`data: [ERROR]${errorPayload}\n`])
      );

      await act(() => result.current.sendMessage("answer"));

      expect(result.current.status).toBe("error");
      expect(result.current.error?.message).toContain("API key");
    });

    it("handles null response body", async () => {
      const { result } = await setupWithSession();

      mockedApi.assessmentRespond.mockResolvedValueOnce({
        ok: true,
        body: null,
      } as unknown as Response);

      await act(() => result.current.sendMessage("answer"));

      expect(result.current.status).toBe("error");
      expect(result.current.error?.message).toBe("No response body");
    });

    it("handles non-Error throw with fallback message", async () => {
      const { result } = await setupWithSession();

      mockedApi.assessmentRespond.mockRejectedValueOnce("string thrown");

      await act(() => result.current.sendMessage("answer"));

      expect(result.current.status).toBe("error");
      expect(result.current.error?.message).toBe("Unknown error occurred");
    });

    it("ignores lines that do not start with 'data: '", async () => {
      const { result } = await setupWithSession();

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse([
          "event: message\n",
          "data: Hello\n",
          "id: 123\n",
          "data: World\n",
        ])
      );

      await act(() => result.current.sendMessage("answer"));

      // Only data: lines contribute to content
      expect(result.current.messages[2].content).toBe("HelloWorld");
    });

    it("exposes sessionId in return value after init", async () => {
      const { result } = await setupWithSession();
      expect(result.current.sessionId).toBe("sess-1");
    });
  });

  describe("message IDs", () => {
    it("generates unique incrementing IDs", async () => {
      mockedApi.assessmentStart.mockResolvedValueOnce({
        sessionId: "sess-1",
        question: "Q1",
        questionType: "open",
        step: 1,
        totalSteps: 3,
      });

      const { result } = renderHook(() => useAssessmentChat(defaultOpts));
      await act(() => result.current.initialiseChat());

      mockedApi.assessmentRespond.mockResolvedValueOnce(
        createSSEResponse(["data: Response\n"])
      );
      await act(() => result.current.sendMessage("answer"));

      const ids = result.current.messages.map((m) => m.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);

      // IDs should be incrementing numeric strings
      const numericIds = ids.map(Number);
      for (let i = 1; i < numericIds.length; i++) {
        expect(numericIds[i]).toBeGreaterThan(numericIds[i - 1]);
      }
    });
  });
});
