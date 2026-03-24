"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, ClipboardCheck } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center space-y-6">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-border bg-card">
        <ClipboardCheck className="h-8 w-8 text-cyan" />
      </div>
      <div className="space-y-2 max-w-sm">
        <h3 className="font-heading text-xl font-semibold">
          No assessments yet
        </h3>
        <p className="text-sm text-muted-foreground">
          Start your first skill assessment to discover your knowledge gaps and
          get a personalized learning plan.
        </p>
      </div>
      <Button
        asChild
        size="lg"
        className="bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2"
      >
        <Link href="/">
          Start Assessment
          <ArrowRight className="h-4 w-4" />
        </Link>
      </Button>
    </div>
  );
}
