"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { ChatMessage } from "@/components/assessment/ChatMessage";
import { AssessmentComplete } from "@/components/assessment/AssessmentComplete";
import { TypingIndicator } from "@/components/assessment/TypingIndicator";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ProficiencyScore } from "@/lib/types";
import { useDemoAssessmentChat } from "@/hooks/useDemoAssessmentChat";
import { Progress } from "@/components/ui/progress";
import { DemoOnboardingDialog } from "@/components/demo/DemoOnboardingDialog";
import { DEMO_STEPS } from "@/lib/demo/constants";
import { Send, Bot } from "lucide-react";

export default function DemoAssessPage() {
  const router = useRouter();

  const [popupDismissed, setPopupDismissed] = useState(() => {
    if (typeof window === "undefined") return false;
    return sessionStorage.getItem("demo-onboarding-seen") === "true";
  });
  const [assessmentDone, setAssessmentDone] = useState(false);
  const [scores, setScores] = useState<ProficiencyScore[]>([]);
  const [inputValue, setInputValue] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const onAssessmentComplete = useCallback(
    (extractedScores: ProficiencyScore[]) => {
      setScores(extractedScores);
      setAssessmentDone(true);
    },
    []
  );

  const { messages, sendMessage, status, error, initialiseChat, progress } =
    useDemoAssessmentChat({
      onAssessmentComplete,
    });

  const isLoading = status === "submitted" || status === "streaming";

  const handlePopupDismiss = useCallback(() => {
    sessionStorage.setItem("demo-onboarding-seen", "true");
    setPopupDismissed(true);
  }, []);

  useEffect(() => {
    if (messages.length === 0 && status === "ready" && popupDismissed) {
      initialiseChat();
    }
  }, [messages.length, status, initialiseChat, popupDismissed]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleContinue = () => {
    router.push("/demo/report");
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

  return (
    <PageShell currentStep={0} noPadding isDemo steps={DEMO_STEPS}>
      <div className="flex h-[calc(100dvh_-_var(--header-h))] flex-col">
        {/* Header */}
        <div className="border-b border-border px-4 py-3 sm:px-6">
          <h2 className="font-heading text-lg font-semibold">
            Demo Assessment
          </h2>
          <p className="text-sm text-muted-foreground">
            Scripted demo — answers don&apos;t affect results
          </p>
        </div>

        {/* Progress Bar */}
        {progress && !assessmentDone && (
          <div className="border-b border-border px-4 py-2 sm:px-6">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
              <span>
                {`Question ${(progress.totalQuestions ?? 0) + 1} of ~${progress.maxQuestions ?? 25}`}
              </span>
              <span>
                {`${Math.round((((progress.totalQuestions ?? 0) + 1) / (progress.maxQuestions ?? 25)) * 100)}%`}
              </span>
            </div>
            <Progress
              value={(((progress.totalQuestions ?? 0) + 1) / (progress.maxQuestions ?? 25)) * 100}
              className="h-1.5"
            />
          </div>
        )}

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
                  placeholder="Type anything — demo responses are scripted..."
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

      <DemoOnboardingDialog
        open={!popupDismissed}
        onDismiss={handlePopupDismiss}
      />
    </PageShell>
  );
}
