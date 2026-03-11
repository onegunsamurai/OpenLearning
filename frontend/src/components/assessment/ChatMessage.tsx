"use client";

import { cn } from "@/lib/utils";
import { motion } from "motion/react";
import { Bot, User } from "lucide-react";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
}

export function ChatMessage({ role, content }: ChatMessageProps) {
  const isAI = role === "assistant";

  return (
    <motion.div
      className={cn("flex gap-3", isAI ? "justify-start" : "justify-end")}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {isAI && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-cyan bg-cyan-muted">
          <Bot className="h-4 w-4 text-cyan" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isAI
            ? "border border-cyan/20 bg-card text-foreground"
            : "bg-cyan text-background"
        )}
      >
        <div className="whitespace-pre-wrap">{content}</div>
      </div>
      {!isAI && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      )}
    </motion.div>
  );
}
