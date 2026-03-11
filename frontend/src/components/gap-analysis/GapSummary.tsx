"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";

interface GapSummaryProps {
  readiness: number;
  summary: string;
}

export function GapSummary({ readiness, summary }: GapSummaryProps) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 1500;
    const start = performance.now();

    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.round(eased * readiness));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [readiness]);

  const getColor = () => {
    if (readiness >= 75) return "text-green-400";
    if (readiness >= 50) return "text-yellow-400";
    return "text-red-400";
  };

  return (
    <motion.div
      className="text-center space-y-3"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <div className="relative inline-flex items-center justify-center">
        <svg className="h-32 w-32 -rotate-90" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="8"
          />
          <motion.circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeLinecap="round"
            className={getColor()}
            strokeDasharray={`${2 * Math.PI * 50}`}
            initial={{ strokeDashoffset: 2 * Math.PI * 50 }}
            animate={{
              strokeDashoffset:
                2 * Math.PI * 50 - (readiness / 100) * 2 * Math.PI * 50,
            }}
            transition={{ duration: 1.5, ease: "easeOut" }}
          />
        </svg>
        <span className={`absolute text-3xl font-heading font-bold ${getColor()}`}>
          {displayValue}%
        </span>
      </div>
      <h3 className="font-heading text-lg font-semibold">Overall Readiness</h3>
      <p className="text-sm text-muted-foreground max-w-md mx-auto">
        {summary}
      </p>
    </motion.div>
  );
}
