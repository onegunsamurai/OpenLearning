"use client";

import Image from "next/image";
import { useAuthStore } from "@/lib/auth-store";
import { useApiKeySetupContext } from "@/components/layout/PageShell";
import { Key, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ProfileCard() {
  const { user } = useAuthStore();
  const { openApiKeySetup } = useApiKeySetupContext();

  if (!user) return null;

  return (
    <div className="rounded-xl border border-border bg-card p-6 space-y-4">
      <div className="flex items-center gap-4">
        {user.avatarUrl ? (
          <Image
            src={user.avatarUrl}
            alt={user.displayName}
            width={48}
            height={48}
            className="h-12 w-12 rounded-full border border-border"
          />
        ) : (
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-border bg-muted text-lg font-medium">
            {user.displayName[0]?.toUpperCase()}
          </div>
        )}
        <div>
          <h2 className="font-heading text-lg font-semibold">
            {user.displayName}
          </h2>
          {user.email && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Mail className="h-3.5 w-3.5" />
              {user.email}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-sm">
          <Key className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">API Key:</span>
          <span
            className={
              user.hasApiKey ? "text-emerald-400" : "text-red-400"
            }
          >
            {user.hasApiKey ? "Configured" : "Not set"}
          </span>
        </div>
        {!user.hasApiKey && (
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            onClick={openApiKeySetup}
          >
            Set up
          </Button>
        )}
      </div>
    </div>
  );
}
