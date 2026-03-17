"use client";

import { useState, useCallback, useRef } from "react";
import { ProficiencyScore } from "@/lib/types";
import {
  DEMO_QUESTIONS,
  DEMO_ASSESSMENT_START,
  DEMO_ASSESSMENT_REPORT,
} from "@/lib/demo/fixtures";
import { createDemoSSEResponse } from "@/lib/demo/demo-assessment";
import type { ChatMessage, AssessmentProgress } from "./useAssessmentChat";

type ChatStatus = "ready" | "submitted" | "streaming" | "error";

interface UseDemoAssessmentChatOptions {
  onAssessmentComplete?: (scores: ProficiencyScore[]) => void;
}

export function useDemoAssessmentChat({
  onAssessmentComplete,
}: UseDemoAssessmentChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>("ready");
  const [error, setError] = useState<Error | null>(null);
  const [progress, setProgress] = useState<AssessmentProgress | null>(null);
  const demoStepRef = useRef(0);
  const idCounter = useRef(0);

  const nextId = () => String(++idCounter.current);

  const initialiseChat = useCallback(() => {
    demoStepRef.current = 0;
    setMessages([
      {
        id: nextId(),
        role: "assistant",
        content: DEMO_ASSESSMENT_START.question,
      },
    ]);
    setProgress({ type: "calibration", step: 1, totalSteps: 3 });
    setStatus("ready");
    setError(null);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const userMessage: ChatMessage = {
        id: nextId(),
        role: "user",
        content: text,
      };
      const assistantId = nextId();

      setMessages((prev) => [...prev, userMessage]);
      setStatus("submitted");
      setError(null);

      try {
        const step = demoStepRef.current;
        const isFinal = step >= DEMO_QUESTIONS.length - 1;
        demoStepRef.current++;

        const response = createDemoSSEResponse(step, isFinal);
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        setStatus("streaming");
        const decoder = new TextDecoder();
        let accumulated = "";

        setMessages((prev) => [
          ...prev,
          { id: assistantId, role: "assistant", content: "" },
        ]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") continue;
              if (data.startsWith("[META]")) {
                try {
                  const meta = JSON.parse(data.slice(6));
                  setProgress({
                    type: meta.type ?? "assessment",
                    step: meta.step,
                    totalSteps: meta.total_steps,
                    topicsEvaluated: meta.topics_evaluated,
                    totalQuestions: meta.total_questions,
                    maxQuestions: meta.max_questions,
                  });
                } catch {
                  // ignore malformed meta
                }
                continue;
              }
              if (data === "[ASSESSMENT_COMPLETE]") {
                onAssessmentComplete?.(DEMO_ASSESSMENT_REPORT.proficiencyScores);
                continue;
              }
              if (data.startsWith("```json")) continue;
              if (data.startsWith("```")) continue;
              if (data.startsWith("{") && accumulated.includes("[ASSESSMENT_COMPLETE]"))
                continue;
              accumulated += data;
              const currentText = accumulated;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: currentText } : m
                )
              );
            }
          }
        }

        setStatus("ready");
      } catch (err) {
        setStatus("error");
        setError(
          err instanceof Error ? err : new Error("Unknown error occurred")
        );
      }
    },
    [onAssessmentComplete]
  );

  return {
    messages,
    sendMessage,
    status,
    error,
    initialiseChat,
    sessionId: "demo-session-001",
    progress,
  };
}
