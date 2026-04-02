"use client";

import { useState, useId } from "react";
import { MarkdownBody } from "./markdown-body";
import { cn } from "@/lib/utils";
import { Lightbulb, ChevronDown } from "lucide-react";
import type { ContentSection } from "@/lib/materials";

interface SectionProps {
  section: ContentSection;
}

export function ExplanationSection({ section }: SectionProps) {
  return (
    <div className="space-y-2">
      <h5 className="text-sm font-medium text-foreground">{section.title}</h5>
      <MarkdownBody content={section.body} />
    </div>
  );
}

export function CodeExampleSection({ section }: SectionProps) {
  return (
    <div className="space-y-2">
      <h5 className="text-sm font-medium text-foreground">{section.title}</h5>
      <MarkdownBody content={section.body} />
      {section.code_block && (
        <pre className="overflow-x-auto rounded-lg border border-border bg-secondary p-3 text-xs font-mono text-foreground">
          <code>{section.code_block}</code>
        </pre>
      )}
    </div>
  );
}

export function AnalogySection({ section }: SectionProps) {
  return (
    <div className="space-y-2 rounded-lg border-l-2 border-cyan pl-4">
      <div className="flex items-center gap-2">
        <Lightbulb className="h-4 w-4 text-cyan" />
        <h5 className="text-sm font-medium text-foreground">{section.title}</h5>
      </div>
      <MarkdownBody content={section.body} />
    </div>
  );
}

export function QuizSection({ section }: SectionProps) {
  const [showAnswer, setShowAnswer] = useState(false);
  const answerId = useId();

  return (
    <div className="space-y-2 rounded-lg border border-border bg-secondary/50 p-3">
      <h5 className="text-sm font-medium text-foreground">{section.title}</h5>
      <MarkdownBody content={section.body} />
      {section.answer && (
        <div>
          <button
            onClick={() => setShowAnswer(!showAnswer)}
            className="flex items-center gap-1 text-xs font-medium text-cyan hover:underline"
            aria-expanded={showAnswer}
            aria-controls={answerId}
          >
            <ChevronDown
              className={cn(
                "h-3 w-3 transition-transform",
                showAnswer && "rotate-180"
              )}
            />
            {showAnswer ? "Hide Answer" : "Show Answer"}
          </button>
          <div id={answerId}>
            {showAnswer && (
              <div className="mt-2 rounded border border-border bg-card p-2">
                <MarkdownBody content={section.answer} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
