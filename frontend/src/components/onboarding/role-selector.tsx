"use client";

import { useEffect, useState } from "react";
import { RoleSummary } from "@/lib/types";
import { api } from "@/lib/api";
import { Loader2, AlertCircle } from "lucide-react";
import { motion } from "motion/react";

const LEVELS = ["junior", "mid", "senior", "staff"] as const;

const LEVEL_LABELS: Record<string, string> = {
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  staff: "Staff",
};

interface RoleSelectorProps {
  selectedRoleId: string | null;
  onSelectRole: (roleId: string, skillIds: string[]) => void;
  targetLevel: string;
  onTargetLevelChange: (level: string) => void;
}

export function RoleSelector({
  selectedRoleId,
  onSelectRole,
  targetLevel,
  onTargetLevelChange,
}: RoleSelectorProps) {
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getRoles()
      .then((data) => {
        setRoles(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load roles");
        setLoading(false);
      });
  }, []);

  const handleCardClick = async (roleId: string) => {
    try {
      const detail = await api.getRole(roleId);
      onSelectRole(roleId, detail.mappedSkillIds);
    } catch {
      setError("Failed to load role details");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">
          Loading roles...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
        <AlertCircle className="h-4 w-4 shrink-0" />
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        {roles.map((role, i) => {
          const isSelected = selectedRoleId === role.id;
          return (
            <motion.button
              key={role.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => handleCardClick(role.id)}
              className={`rounded-lg border p-4 text-left transition-colors cursor-pointer ${
                isSelected
                  ? "border-cyan bg-cyan-muted"
                  : "border-border bg-secondary hover:border-muted-foreground/30"
              }`}
            >
              <h4 className="font-semibold text-sm">{role.name}</h4>
              <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                {role.description}
              </p>
              <p className="mt-2 text-xs font-mono text-muted-foreground">
                {role.skillCount} skills
              </p>
            </motion.button>
          );
        })}
      </div>

      <div>
        <p className="mb-2 text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
          Target Level
        </p>
        <div className="flex rounded-lg border border-border overflow-hidden">
          {LEVELS.map((level) => (
            <button
              key={level}
              onClick={() => onTargetLevelChange(level)}
              className={`flex-1 px-3 py-2 text-xs font-semibold transition-colors cursor-pointer ${
                targetLevel === level
                  ? "bg-cyan text-background"
                  : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              {LEVEL_LABELS[level]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
