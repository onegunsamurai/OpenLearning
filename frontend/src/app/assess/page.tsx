"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { ChatMessage } from "@/components/assessment/ChatMessage";
import { AssessmentComplete } from "@/components/assessment/AssessmentComplete";
import { TypingIndicator } from "@/components/assessment/TypingIndicator";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAppStore } from "@/lib/store";
import { useAuthStore } from "@/lib/auth-store";
import { useAuth } from "@/hooks/useAuth";
import { ProficiencyScore } from "@/lib/types";
import { useAssessmentChat } from "@/hooks/useAssessmentChat";
import { Progress } from "@/components/ui/progress";
import { Send, Bot } from "lucide-react";
export default function AssessPage() {
  const router = useRouter();
  const {
    selectedSkillIds,
    setProficiencyScores,
    setCurrentStep,
    setAssessmentSessionId,
    targetLevel,
    selectedRoleId,
  } = useAppStore();

  const { user, isLoading: authLoading } = useAuthStore();
  const { login } = useAuth();

  const [assessmentDone, setAssessmentDone] = useState(false);
  const [scores, setScores] = useState<ProficiencyScore[]>([]);
  const [inputValue, setInputValue] = useState("");
  const needsApiKey = !!user && !user.hasApiKey;
  const bottomRef = useRef<HTMLDivElement>(null);

  const onAssessmentComplete = useCallback(
    (extractedScores: ProficiencyScore[]) => {
      setScores(extractedScores);
      setProficiencyScores(extractedScores);
      setAssessmentDone(true);
    },
    [setProficiencyScores]
  );

  const { messages, sendMessage, status, error, initialiseChat, sessionId, progress } =
    useAssessmentChat({
      skillIds: selectedSkillIds,
      targetLevel,
      roleId: selectedRoleId,
      onAssessmentComplete,
    });

  // Store session ID
  useEffect(() => {
    if (sessionId) {
      setAssessmentSessionId(sessionId);
    }
  }, [sessionId, setAssessmentSessionId]);

  const isLoading = status === "submitted" || status === "streaming";

  useEffect(() => {
    if (selectedSkillIds.length > 0 && messages.length === 0 && status === "ready" && !needsApiKey) {
      initialiseChat();
    }
  }, [selectedSkillIds.length, messages.length, status, initialiseChat, needsApiKey]);

  useEffect(() => {
    if (!authLoading && !user) {
      login("/assess");
    }
  }, [authLoading, user, login]);

  useEffect(() => {
    if (selectedSkillIds.length === 0) {
      router.push("/");
    }
  }, [selectedSkillIds, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleContinue = () => {
    setCurrentStep(2);
    router.push("/gap-analysis");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;
    sendMessage(inputValue);
    setInputValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  if (authLoading || !user) return null;
  if (selectedSkillIds.length === 0) return null;

  return (
    <PageShell currentStep={1} noPadding autoPromptApiKey onApiKeySet={initialiseChat}>
      <div className="flex h-[calc(100vh-57px)] flex-col">
        {/* Header */}
        <div className="border-b border-border px-4 py-3 sm:px-6">
          <h2 className="font-heading text-lg font-semibold">
            Skill Assessment
          </h2>
          <p className="text-sm text-muted-foreground">
            Assessing {selectedSkillIds.length} skill
            {selectedSkillIds.length !== 1 ? "s" : ""}
          </p>
        </div>

        {/* Progress Bar */}
        {progress && !assessmentDone && (() => {
          const assessmentPercent = progress.type === "assessment"
            ? (((progress.totalQuestions ?? 0) + 1) / (progress.maxQuestions ?? 25)) * 100
            : 0;
          const isOverflowing = progress.type === "assessment" && assessmentPercent >= 95;

          return (
            <div className="border-b border-border px-4 py-2 sm:px-6">
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
                <span>
                  {progress.type === "calibration"
                    ? `Calibration: Step ${progress.step ?? 1} of ${progress.totalSteps ?? 3}`
                    : `Question ${(progress.totalQuestions ?? 0) + 1} of ~${progress.maxQuestions ?? 25}`}
                </span>
                <span>
                  {progress.type === "calibration"
                    ? `${Math.round(((progress.step ?? 1) / (progress.totalSteps ?? 3)) * 100)}%`
                    : isOverflowing
                      ? "Almost done"
                      : `${Math.round(assessmentPercent)}%`}
                </span>
              </div>
              <Progress
                value={
                  progress.type === "calibration"
                    ? ((progress.step ?? 1) / (progress.totalSteps ?? 3)) * 100
                    : Math.min(assessmentPercent, 95)
                }
                className="h-1.5"
              />
            </div>
          );
        })()}

        {assessmentDone ? (
          <div className="flex-1 overflow-y-auto">
            <AssessmentComplete scores={scores} onContinue={handleContinue} />
          </div>
        ) : (
          <>
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg) => {
                const displayText = msg.content
                  .replace(/\[ASSESSMENT_COMPLETE\][\s\S]*$/, "")
                  .trim();
                if (!displayText) return null;
                return (
                  <ChatMessage
                    key={msg.id}
                    role={msg.role}
                    content={displayText}
                  />
                );
              })}
              {isLoading &&
                messages.length > 0 &&
                messages[messages.length - 1]?.role === "user" && (
                  <div className="flex gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-cyan bg-cyan-muted">
                      <Bot className="h-4 w-4 text-cyan" />
                    </div>
                    <TypingIndicator />
                  </div>
                )}
              <div ref={bottomRef} />
            </div>

            {/* Error */}
            {error && (
              <div className="mx-4 mb-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                Error: {error.message}
              </div>
            )}

            {/* Input */}
            <div className="border-t border-border p-4 sm:px-6">
              <form onSubmit={handleSubmit} className="flex items-end gap-3">
                <Textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your answer..."
                  className="min-h-[44px] max-h-[120px] resize-none bg-secondary border-border"
                  rows={1}
                />
                <Button
                  type="submit"
                  disabled={isLoading || !inputValue.trim()}
                  className="bg-cyan text-background hover:bg-cyan/90 h-11 w-11 shrink-0 p-0"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </form>
            </div>
          </>
        )}
      </div>
    </PageShell>
  );
}
