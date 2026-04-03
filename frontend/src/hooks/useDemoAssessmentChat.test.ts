import { renderHook, act } from "@testing-library/react";
import { vi } from "vitest";
import { useDemoAssessmentChat } from "./useDemoAssessmentChat";
import {
  DEMO_ASSESSMENT_START,
  DEMO_QUESTIONS,
  DEMO_ASSESSMENT_REPORT,
} from "@/lib/demo/fixtures";

describe("useDemoAssessmentChat", () => {
  describe("initial state", () => {
    it("starts with empty messages, ready status, no error, no progress", () => {
      const { result } = renderHook(() => useDemoAssessmentChat());
      expect(result.current.messages).toEqual([]);
      expect(result.current.status).toBe("ready");
      expect(result.current.error).toBeNull();
      expect(result.current.progress).toBeNull();
    });

    it("returns demo session ID", () => {
      const { result } = renderHook(() => useDemoAssessmentChat());
      expect(result.current.sessionId).toBe("demo-session-001");
    });
  });

  describe("initialiseChat", () => {
    it("sets first message from fixture", () => {
      const { result } = renderHook(() => useDemoAssessmentChat());

      act(() => result.current.initialiseChat());

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].role).toBe("assistant");
      expect(result.current.messages[0].content).toBe(
        DEMO_ASSESSMENT_START.question
      );
    });

    it("sets initial assessment progress", () => {
      const { result } = renderHook(() => useDemoAssessmentChat());

      act(() => result.current.initialiseChat());

      expect(result.current.progress).toEqual({
        type: "assessment",
        totalQuestions: 1,
        maxQuestions: DEMO_QUESTIONS.length,
      });
    });

    it("resets state when called again", async () => {
      const { result } = renderHook(() => useDemoAssessmentChat());

      act(() => result.current.initialiseChat());
      await act(() => result.current.sendMessage("answer"));

      expect(result.current.messages.length).toBeGreaterThan(1);

      act(() => result.current.initialiseChat());

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].content).toBe(
        DEMO_ASSESSMENT_START.question
      );
    });
  });

  describe("sendMessage", () => {
    it("adds user message and streams assistant response", async () => {
      const { result } = renderHook(() => useDemoAssessmentChat());

      act(() => result.current.initialiseChat());
      await act(() => result.current.sendMessage("my answer"));

      // Should have: initial assistant + user + streamed assistant
      expect(result.current.messages).toHaveLength(3);
      expect(result.current.messages[1].role).toBe("user");
      expect(result.current.messages[1].content).toBe("my answer");
      expect(result.current.messages[2].role).toBe("assistant");
      expect(result.current.messages[2].content.length).toBeGreaterThan(0);
    });

    it("returns to ready status after streaming", async () => {
      const { result } = renderHook(() => useDemoAssessmentChat());

      act(() => result.current.initialiseChat());
      await act(() => result.current.sendMessage("answer"));

      expect(result.current.status).toBe("ready");
    });

    it("advances through demo questions", async () => {
      const { result } = renderHook(() => useDemoAssessmentChat());

      act(() => result.current.initialiseChat());

      // Send 3 messages
      for (let i = 0; i < 3; i++) {
        await act(() => result.current.sendMessage(`answer ${i}`));
      }

      // Check that progress has updated
      expect(result.current.progress).not.toBeNull();
    });
  });

  describe("onAssessmentComplete", () => {
    it("fires with fixture scores on final question", async () => {
      const onComplete = vi.fn();
      const { result } = renderHook(() =>
        useDemoAssessmentChat({ onAssessmentComplete: onComplete })
      );

      act(() => result.current.initialiseChat());

      // Send all demo questions
      for (let i = 0; i < DEMO_QUESTIONS.length; i++) {
        await act(() => result.current.sendMessage(`answer ${i}`));
      }

      expect(onComplete).toHaveBeenCalledWith(
        DEMO_ASSESSMENT_REPORT.proficiencyScores
      );
    });

    it("does not fire before final question", async () => {
      const onComplete = vi.fn();
      const { result } = renderHook(() =>
        useDemoAssessmentChat({ onAssessmentComplete: onComplete })
      );

      act(() => result.current.initialiseChat());

      // Send all but the last question
      for (let i = 0; i < DEMO_QUESTIONS.length - 1; i++) {
        await act(() => result.current.sendMessage(`answer ${i}`));
      }

      expect(onComplete).not.toHaveBeenCalled();
    });
  });

  describe("message IDs", () => {
    it("generates unique incrementing IDs", async () => {
      const { result } = renderHook(() => useDemoAssessmentChat());

      act(() => result.current.initialiseChat());
      await act(() => result.current.sendMessage("answer"));

      const ids = result.current.messages.map((m) => m.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);

      const numericIds = ids.map(Number);
      for (let i = 1; i < numericIds.length; i++) {
        expect(numericIds[i]).toBeGreaterThan(numericIds[i - 1]);
      }
    });
  });
});
