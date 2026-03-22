"use client";

import { useState, createContext, useContext } from "react";
import { StepProgress, type StepDefinition } from "./StepProgress";
import { motion } from "motion/react";
import Image from "next/image";
import Link from "next/link";
import { LogOut, Key } from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { useAuth } from "@/hooks/useAuth";
import { ApiKeySetup } from "@/components/settings/api-key-setup";
import { api } from "@/lib/api";

const ApiKeySetupContext = createContext<{ openApiKeySetup: () => void }>({
  openApiKeySetup: () => {},
});

export const useApiKeySetupContext = () => useContext(ApiKeySetupContext);

interface PageShellProps {
  currentStep?: number;
  children: React.ReactNode;
  maxWidth?: string;
  noPadding?: boolean;
  isDemo?: boolean;
  steps?: StepDefinition[];
  autoPromptApiKey?: boolean;
  onApiKeySet?: () => void;
}

export function PageShell({
  currentStep,
  children,
  maxWidth = "max-w-7xl",
  noPadding = false,
  isDemo = false,
  steps,
  autoPromptApiKey = false,
  onApiKeySet,
}: PageShellProps) {
  const { user, isLoading, setUser } = useAuthStore();
  const { login, logout } = useAuth();
  const [manualShowKeySetup, setManualShowKeySetup] = useState(false);
  const [autoPromptDismissed, setAutoPromptDismissed] = useState(false);

  const shouldAutoPrompt =
    autoPromptApiKey && !!user && !user.hasApiKey && !autoPromptDismissed;
  const showKeySetup = manualShowKeySetup || shouldAutoPrompt;

  const handleKeySet = async () => {
    try {
      const me = await api.authMe();
      setUser(me);
      onApiKeySet?.();
    } catch { /* ignore */ }
  };

  return (
    <div className="grid-background min-h-screen">
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className={`mx-auto flex items-center justify-between ${maxWidth} px-4 py-3 sm:px-6`}>
          <div className="flex items-center gap-3">
            <Link href="/">
              <h1 className="font-heading text-lg font-bold tracking-tight">
                <span className="text-cyan">Open</span>Learning
              </h1>
            </Link>
            {isDemo && (
              <span className="rounded border border-amber-500/50 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-amber-400">
                Demo
              </span>
            )}
          </div>

          <div className="flex items-center gap-4">
            {currentStep !== undefined && (
              <StepProgress currentStep={currentStep} steps={steps} />
            )}
            {!isDemo && (
              <div className="flex items-center gap-2">
                {isLoading ? (
                  <div className="h-8 w-24 animate-pulse rounded-full bg-muted" />
                ) : user ? (
                  <div className="flex items-center gap-2">
                    {user.avatarUrl ? (
                      <Image
                        src={user.avatarUrl}
                        alt={user.displayName}
                        width={28}
                        height={28}
                        className="h-7 w-7 rounded-full border border-border"
                      />
                    ) : (
                      <div className="flex h-7 w-7 items-center justify-center rounded-full border border-border bg-muted text-xs font-medium">
                        {user.displayName[0]?.toUpperCase()}
                      </div>
                    )}
                    <span className="hidden text-sm text-muted-foreground sm:block">
                      {user.displayName}
                    </span>
                    <button
                      onClick={() => setManualShowKeySetup(true)}
                      className="relative inline-flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:text-foreground"
                      aria-label="API key settings"
                    >
                      <Key className="h-3.5 w-3.5" />
                      <span
                        className={`absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-background ${
                          user.hasApiKey ? "bg-emerald-500" : "bg-red-500"
                        }`}
                      />
                    </button>
                    <button
                      onClick={logout}
                      className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border px-3 text-xs text-muted-foreground transition-colors hover:text-foreground"
                    >
                      <LogOut className="h-3 w-3" />
                      <span className="hidden sm:inline">Sign Out</span>
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => login(window.location.pathname)}
                    className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border px-3.5 text-[13px] font-medium text-muted-foreground transition-colors hover:text-foreground"
                  >
                    Sign in
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </header>
      <ApiKeySetupContext.Provider
        value={{ openApiKeySetup: () => setManualShowKeySetup(true) }}
      >
        <motion.main
          className={noPadding ? "" : `mx-auto ${maxWidth} px-4 py-8 sm:px-6`}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
        >
          {children}
        </motion.main>
      </ApiKeySetupContext.Provider>
      <ApiKeySetup
        open={showKeySetup}
        onClose={() => {
          setManualShowKeySetup(false);
          setAutoPromptDismissed(true);
        }}
        onKeySet={handleKeySet}
      />
    </div>
  );
}
