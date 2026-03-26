"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import { motion } from "motion/react";

interface SkillTagProps {
  name: string;
  selected: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export function SkillTag({ name, selected, onToggle, disabled }: SkillTagProps) {
  return (
    <motion.button
      onClick={onToggle}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-all",
        disabled && "opacity-40 cursor-not-allowed",
        selected
          ? "border-cyan bg-cyan-muted text-cyan"
          : "border-border bg-secondary text-muted-foreground hover:border-cyan/50 hover:text-foreground"
      )}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      layout
    >
      {selected && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 500, damping: 25 }}
        >
          <Check className="h-3.5 w-3.5" />
        </motion.span>
      )}
      {name}
    </motion.button>
  );
}
