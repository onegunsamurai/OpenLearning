"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { SkillTag } from "./SkillTag";
import { Skill } from "@/lib/types";
import { api } from "@/lib/api";
import { Loader2, FileText } from "lucide-react";

interface JDPasteInputProps {
  skills: Skill[];
  selectedSkillIds: string[];
  onSkillsExtracted: (skillIds: string[]) => void;
  onToggleSkill: (skillId: string) => void;
}

export function JDPasteInput({
  skills,
  selectedSkillIds,
  onSkillsExtracted,
  onToggleSkill,
}: JDPasteInputProps) {
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractedSkills, setExtractedSkills] = useState<string[]>([]);
  const [summary, setSummary] = useState("");

  const handleAnalyse = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const data = await api.parseJD(jd);
      setExtractedSkills(data.skills);
      setSummary(data.summary);
      onSkillsExtracted(data.skills);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Textarea
        placeholder="Paste a job description here to auto-detect required skills..."
        value={jd}
        onChange={(e) => setJd(e.target.value)}
        className="min-h-[140px] bg-secondary border-border resize-none font-mono text-sm"
      />
      <Button
        onClick={handleAnalyse}
        disabled={loading || !jd.trim()}
        className="w-full bg-cyan text-background hover:bg-cyan/90 font-semibold"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : (
          <FileText className="h-4 w-4 mr-2" />
        )}
        {loading ? "Analysing..." : "Analyse JD"}
      </Button>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button
            onClick={handleAnalyse}
            className="ml-2 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {summary && (
        <p className="text-sm text-muted-foreground italic">{summary}</p>
      )}

      {extractedSkills.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Extracted Skills
          </h4>
          <div className="flex flex-wrap gap-2">
            {extractedSkills.map((skillId) => {
              const skill = skills.find((s) => s.id === skillId);
              return (
                <SkillTag
                  key={skillId}
                  name={skill?.name ?? skillId}
                  selected={selectedSkillIds.includes(skillId)}
                  onToggle={() => onToggleSkill(skillId)}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
