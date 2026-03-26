"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { SkillTag } from "./SkillTag";
import { Search } from "lucide-react";
import { motion } from "motion/react";
import type { ConceptSummary } from "@/lib/types";

const LEVEL_LABELS: Record<string, string> = {
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  staff: "Staff",
};

interface ConceptBrowserProps {
  concepts: ConceptSummary[];
  selectedConceptIds: string[];
  onToggleConcept: (conceptId: string) => void;
  maxSelections?: number;
}

export function ConceptBrowser({
  concepts,
  selectedConceptIds,
  onToggleConcept,
  maxSelections = 10,
}: ConceptBrowserProps) {
  const [search, setSearch] = useState("");

  const filtered = search
    ? concepts.filter((c) =>
        c.displayName.toLowerCase().includes(search.toLowerCase())
      )
    : concepts;

  // Group by level, preserving topological order within each group
  const levels = [...new Set(concepts.map((c) => c.level))];
  const groupedByLevel = levels
    .map((level) => ({
      level,
      label: LEVEL_LABELS[level] ?? level,
      concepts: filtered.filter((c) => c.level === level),
    }))
    .filter((g) => g.concepts.length > 0);

  const atLimit = selectedConceptIds.length >= maxSelections;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search topics..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-secondary border-border"
          />
        </div>
        <span className="ml-3 text-xs font-mono text-muted-foreground whitespace-nowrap">
          {selectedConceptIds.length}/{maxSelections} selected
        </span>
      </div>
      <div className="space-y-5 max-h-[300px] sm:max-h-[400px] overflow-y-auto pr-2">
        {groupedByLevel.map((group, gi) => (
          <motion.div
            key={group.level}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: gi * 0.05 }}
          >
            <h3 className="mb-2 text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
              {group.label}
            </h3>
            <div className="flex flex-wrap gap-2">
              {group.concepts.map((concept) => {
                const isSelected = selectedConceptIds.includes(concept.id);
                const isDisabled = atLimit && !isSelected;
                return (
                  <SkillTag
                    key={concept.id}
                    name={concept.displayName}
                    selected={isSelected}
                    onToggle={() => {
                      if (!isDisabled) onToggleConcept(concept.id);
                    }}
                    disabled={isDisabled}
                  />
                );
              })}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
