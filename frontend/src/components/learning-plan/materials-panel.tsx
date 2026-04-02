"use client";

import { useState, useId } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, BookText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ParsedMaterial } from "@/lib/materials";
import { QualityBadge } from "./quality-badge";
import { ContentSectionRenderer } from "./content-section-renderer";

interface MaterialsPanelProps {
  material: ParsedMaterial;
}

export function MaterialsPanel({ material }: MaterialsPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();

  return (
    <div className="space-y-2">
      <button
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
        className="flex w-full items-center gap-2 rounded-lg border border-border bg-secondary/50 px-3 py-2 text-left text-xs transition-colors hover:bg-secondary"
        aria-expanded={expanded}
        aria-controls={contentId}
        aria-label="Toggle learning materials"
      >
        <BookText className="h-3.5 w-3.5 text-cyan" />
        <span className="font-medium text-muted-foreground">
          Learning Materials
        </span>
        <QualityBadge
          qualityScore={material.qualityScore}
          qualityFlag={material.qualityFlag}
        />
        <ChevronDown
          className={cn(
            "ml-auto h-3.5 w-3.5 text-muted-foreground transition-transform",
            expanded && "rotate-180"
          )}
        />
      </button>

      <div id={contentId}>
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="space-y-4 pt-1">
                {material.sections.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    No content available
                  </p>
                ) : (
                  material.sections.map((section) => (
                    <ContentSectionRenderer
                      key={`${section.type}-${section.title}`}
                      section={section}
                    />
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
