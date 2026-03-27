"use client";

import { useEffect } from "react";
import Link from "next/link";
import { PageShell } from "@/components/layout/PageShell";
import { ProfileCard } from "@/components/dashboard/ProfileCard";
import { AssessmentCard } from "@/components/dashboard/AssessmentCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { useAuthStore } from "@/lib/auth-store";
import { useAuth } from "@/hooks/useAuth";
import { useUserAssessments } from "@/hooks/useUserAssessments";
import { Button } from "@/components/ui/button";
import { ApiErrorDisplay } from "@/components/error/api-error-display";
import { Loader2, Plus } from "lucide-react";

export default function DashboardPage() {
  const { user, isLoading: authLoading } = useAuthStore();
  const { login } = useAuth();
  const { sessions, loading, error, refetch, deleteSession } = useUserAssessments();

  useEffect(() => {
    if (!authLoading && !user) {
      login("/dashboard");
    }
  }, [authLoading, user, login]);

  if (authLoading || !user) return null;

  return (
    <PageShell>
      <div className="space-y-8">
        <ProfileCard />

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-xl font-semibold">
              Your Assessments
            </h2>
            <Button
              asChild
              size="sm"
              className="bg-cyan text-background hover:bg-cyan/90 gap-1.5"
            >
              <Link href="/">
                <Plus className="h-4 w-4" />
                New Assessment
              </Link>
            </Button>
          </div>

          {loading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-cyan" />
            </div>
          )}

          {error && (
            <div className="flex justify-center py-8">
              <ApiErrorDisplay error={error} onRetry={refetch} />
            </div>
          )}

          {!loading && !error && sessions.length === 0 && <EmptyState />}

          {!loading && !error && sessions.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {sessions.map((session, i) => (
                <AssessmentCard
                  key={session.sessionId}
                  session={session}
                  index={i}
                  onDelete={deleteSession}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </PageShell>
  );
}
