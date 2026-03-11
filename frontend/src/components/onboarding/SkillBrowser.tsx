"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Skill } from "@/lib/types";
import { SkillTag } from "./SkillTag";
import { Search } from "lucide-react";
import { motion } from "motion/react";

interface SkillBrowserProps {
  skills: Skill[];
  categories: string[];
  selectedSkillIds: string[];
  onToggleSkill: (skillId: string) => void;
}

export function SkillBrowser({
  skills,
  categories,
  selectedSkillIds,
  onToggleSkill,
}: SkillBrowserProps) {
  const [search, setSearch] = useState("");

  const filtered = search
    ? skills.filter(
        (s) =>
          s.name.toLowerCase().includes(search.toLowerCase()) ||
          s.category.toLowerCase().includes(search.toLowerCase()) ||
          s.subSkills.some((sub) =>
            sub.toLowerCase().includes(search.toLowerCase())
          )
      )
    : skills;

  const groupedByCategory = categories
    .map((cat) => ({
      category: cat,
      skills: filtered.filter((s) => s.category === cat),
    }))
    .filter((g) => g.skills.length > 0);

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search skills..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 bg-secondary border-border"
        />
      </div>
      <div className="space-y-5 max-h-[400px] overflow-y-auto pr-2">
        {groupedByCategory.map((group, gi) => (
          <motion.div
            key={group.category}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: gi * 0.05 }}
          >
            <h3 className="mb-2 text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
              {group.category}
            </h3>
            <div className="flex flex-wrap gap-2">
              {group.skills.map((skill) => (
                <SkillTag
                  key={skill.id}
                  name={skill.name}
                  selected={selectedSkillIds.includes(skill.id)}
                  onToggle={() => onToggleSkill(skill.id)}
                />
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
