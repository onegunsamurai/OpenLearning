"use client";

import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { GapItem } from "@/lib/types";

interface RadarChartProps {
  gaps: GapItem[];
}

export function RadarChart({ gaps }: RadarChartProps) {
  const data = gaps.map((g) => ({
    skill: g.skillName.length > 12 ? g.skillName.slice(0, 12) + "..." : g.skillName,
    current: g.currentLevel,
    target: g.targetLevel,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <RechartsRadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="rgba(255,255,255,0.1)" />
        <PolarAngleAxis
          dataKey="skill"
          tick={{ fill: "#71717a", fontSize: 11 }}
        />
        <PolarRadiusAxis
          angle={30}
          domain={[0, 100]}
          tick={{ fill: "#71717a", fontSize: 10 }}
        />
        <Radar
          name="Current"
          dataKey="current"
          stroke="#00d4ff"
          fill="#00d4ff"
          fillOpacity={0.2}
        />
        <Radar
          name="Target"
          dataKey="target"
          stroke="#a78bfa"
          fill="#a78bfa"
          fillOpacity={0.1}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, color: "#71717a" }}
        />
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}
