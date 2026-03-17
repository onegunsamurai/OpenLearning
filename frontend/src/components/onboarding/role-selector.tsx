"use client";

import { useEffect, useState, useCallback, useRef } from "react";
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
  getRoles?: () => Promise<RoleSummary[]>;
  getRole?: (roleId: string) => Promise<{ mappedSkillIds: string[] }>;
}

export function RoleSelector({
  selectedRoleId,
  onSelectRole,
  targetLevel,
  onTargetLevelChange,
  getRoles: getRolesOverride,
  getRole: getRoleOverride,
}: RoleSelectorProps) {
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingRoleId, setLoadingRoleId] = useState<string | null>(null);
  const requestCounterRef = useRef(0);

  const fetchRoles = useCallback(() => {
    setLoading(true);
    setError(null);
    (getRolesOverride ?? api.getRoles)()
      .then((data) => {
        setRoles(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load roles");
        setLoading(false);
      });
  }, [getRolesOverride]);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  const handleCardClick = async (roleId: string) => {
    setError(null);
    setLoadingRoleId(roleId);
    const requestId = ++requestCounterRef.current;
    try {
      const detail = await (getRoleOverride ?? api.getRole)(roleId);
      if (requestCounterRef.current !== requestId) return;
      onSelectRole(roleId, detail.mappedSkillIds);
    } catch {
      if (requestCounterRef.current !== requestId) return;
      setError("Failed to load role details");
    } finally {
      if (requestCounterRef.current === requestId) {
        setLoadingRoleId(null);
      }
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

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span className="flex-1">{error}</span>
          {roles.length === 0 && (
            <button
              type="button"
              onClick={fetchRoles}
              className="ml-2 underline font-semibold hover:text-destructive/80"
            >
              Retry
            </button>
          )}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        {roles.map((role, i) => {
          const isSelected = selectedRoleId === role.id;
          const isLoading = loadingRoleId === role.id;
          return (
            <motion.button
              key={role.id}
              type="button"
              aria-pressed={isSelected}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => handleCardClick(role.id)}
              disabled={loadingRoleId !== null}
              className={`rounded-lg border p-4 text-left transition-colors cursor-pointer ${
                isSelected
                  ? "border-cyan bg-cyan-muted"
                  : "border-border bg-secondary hover:border-muted-foreground/30"
              } ${loadingRoleId !== null && !isLoading ? "opacity-50" : ""}`}
            >
              <h4 className="font-semibold text-sm">{role.name}</h4>
              <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                {role.description}
              </p>
              <p className="mt-2 text-xs font-mono text-muted-foreground">
                {isLoading ? (
                  <Loader2 className="inline h-3 w-3 animate-spin" />
                ) : (
                  `${role.skillCount} skills`
                )}
              </p>
            </motion.button>
          );
        })}
      </div>

      <div>
        <p className="mb-2 text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
          Target Level
        </p>
        <div
          className="flex rounded-lg border border-border overflow-hidden"
          role="radiogroup"
          aria-label="Target level"
        >
          {LEVELS.map((level) => (
            <button
              key={level}
              type="button"
              aria-pressed={targetLevel === level}
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
