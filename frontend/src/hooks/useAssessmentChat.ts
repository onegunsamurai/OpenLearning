"use client";

import { useState, useCallback, useRef } from "react";
import { ProficiencyScore } from "@/lib/types";
import { api, ApiError, parseRetryAfter } from "@/lib/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export interface AssessmentProgress {
  type: "calibration" | "assessment";
  step?: number;
  totalSteps?: number;
  topicsEvaluated?: number;
  totalQuestions?: number;
  maxQuestions?: number;
}

type ChatStatus = "ready" | "submitted" | "streaming" | "error";

interface UseAssessmentChatOptions {
  skillIds: string[];
  targetLevel?: string;
  roleId?: string | null;
  onAssessmentComplete?: (scores: ProficiencyScore[]) => void;
}

export function useAssessmentChat({
  skillIds,
  targetLevel,
  roleId,
  onAssessmentComplete,
}: UseAssessmentChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>("ready");
  const [error, setError] = useState<Error | null>(null);
  const [progress, setProgress] = useState<AssessmentProgress | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const idCounter = useRef(0);

  const nextId = () => String(++idCounter.current);

  const initialiseChat = useCallback(async () => {
    setMessages([]);
    setStatus("submitted");
    setError(null);

    try {
      const result = await api.assessmentStart(skillIds, targetLevel, roleId);
      sessionIdRef.current = result.sessionId;
      setProgress({ type: "calibration", step: 1, totalSteps: 3 });

      const assistantId = nextId();
      setMessages([
        { id: assistantId, role: "assistant", content: result.question },
      ]);
      setStatus("ready");
    } catch (err) {
      setStatus("error");
      setError(
        err instanceof Error ? err : new Error("Failed to start assessment")
      );
    }
  }, [skillIds, targetLevel, roleId]);

  const resumeChat = useCallback(async (existingSessionId: string) => {
    setMessages([]);
    setStatus("submitted");
    setError(null);

    try {
      const result = await api.assessmentResume(existingSessionId);
      sessionIdRef.current = result.sessionId;
      setProgress({
        type: result.questionType === "calibration" ? "calibration" : "assessment",
        step: result.step,
        totalSteps: result.totalSteps,
      });

      const assistantId = nextId();
      setMessages([
        { id: assistantId, role: "assistant", content: result.question },
      ]);
      setStatus("ready");
    } catch (err) {
      setStatus("error");
      setError(
        err instanceof Error ? err : new Error("Failed to resume assessment")
      );
    }
  }, []);

  const sendMessage = useCallback(
    async (text: string, { isRetry = false }: { isRetry?: boolean } = {}) => {
      const sessionId = sessionIdRef.current;
      if (!sessionId) {
        setError(new Error("No active session"));
        return;
      }

      const userMessage: ChatMessage = {
        id: nextId(),
        role: "user",
        content: text,
      };
      const assistantId = nextId();

      if (!isRetry) {
        setMessages((prev) => [...prev, userMessage]);
      }
      setStatus("submitted");
      setError(null);

      try {
        const response = await api.assessmentRespond(sessionId, text);

        if (!response.ok) {
          const body = await response
            .json()
            .catch(() => ({ detail: "Request failed" }));
          throw new ApiError(
            body.detail ?? `Assessment request failed: ${response.status}`,
            response.status,
            parseRetryAfter(response.headers?.get("Retry-After"))
          );
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        setStatus("streaming");
        const decoder = new TextDecoder();
        let accumulated = "";
        let buffer = "";
        let reportFetchFailed = false;

        setMessages((prev) => [
          ...prev,
          { id: assistantId, role: "assistant", content: "" },
        ]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

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
              if (data.startsWith("[ERROR]")) {
                try {
                  const errorData = JSON.parse(data.slice(7));
                  throw new ApiError(
                    errorData.detail ?? "An error occurred",
                    errorData.status ?? 500,
                    parseRetryAfter(String(errorData.retryAfter ?? ""))
                  );
                } catch (e) {
                  if (e instanceof ApiError) throw e;
                  throw new ApiError("An error occurred during assessment", 500);
                }
              }
              if (data === "[ASSESSMENT_COMPLETE]") {
                // Assessment done — fetch scores from report
                try {
                  const report = await api.assessmentReport(sessionId);
                  onAssessmentComplete?.(report.proficiencyScores);
                } catch (e) {
                  reportFetchFailed = true;
                  setStatus("error");
                  setError(
                    e instanceof Error
                      ? e
                      : new Error("Failed to fetch assessment report")
                  );
                }
                continue;
              }
              if (data.startsWith("```json")) continue;
              if (data.startsWith("```")) continue;
              // Skip score JSON chunks
              if (data.startsWith("{") && accumulated.includes("[ASSESSMENT_COMPLETE]")) continue;
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

        if (!reportFetchFailed) {
          setStatus("ready");
        }
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
    resumeChat,
    sessionId: sessionIdRef.current,
    progress,
  };
}
