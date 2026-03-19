"use client";

import { useState, useEffect, useCallback } from "react";
import { ApiError } from "@/lib/api";
import { useApiKeySetupContext } from "@/components/layout/PageShell";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw, Key } from "lucide-react";

interface ApiErrorDisplayProps {
  error: Error;
  onRetry?: () => void;
  className?: string;
}

export function ApiErrorDisplay({
  error,
  onRetry,
  className = "",
}: ApiErrorDisplayProps) {
  const { openApiKeySetup } = useApiKeySetupContext();
  const isApiError = error instanceof ApiError;
  const status = isApiError ? error.status : 0;
  const retryAfter = isApiError ? error.retryAfter : undefined;

  const initialCountdown = status === 429 && retryAfter ? retryAfter : null;
  const [countdown, setCountdown] = useState<number | null>(initialCountdown);

  // Reset countdown when error changes — React-recommended pattern for
  // adjusting state when props change (no effect needed).
  const [prevError, setPrevError] = useState(error);
  if (prevError !== error) {
    setPrevError(error);
    setCountdown(initialCountdown);
  }

  const handleAutoRetry = useCallback(() => {
    onRetry?.();
  }, [onRetry]);

  useEffect(() => {
    if (countdown === null || countdown <= 0) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [countdown]);

  useEffect(() => {
    if (countdown === 0) {
      handleAutoRetry();
    }
  }, [countdown, handleAutoRetry]);

  const getErrorContent = () => {
    if (!isApiError) {
      const isNetworkError = error instanceof TypeError;
      return {
        title: isNetworkError ? "Connection Error" : "Something Went Wrong",
        message: isNetworkError
          ? "Cannot reach the server. Check your internet connection and try again."
          : error.message || "An unexpected error occurred.",
        showApiKeyButton: false,
      };
    }

    switch (status) {
      case 401:
        return {
          title: "Invalid API Key",
          message: error.message,
          showApiKeyButton: true,
        };
      case 429:
        return {
          title: "Rate Limited",
          message: error.message,
          showApiKeyButton: false,
        };
      case 502:
      case 504:
        return {
          title: "Service Unavailable",
          message: error.message,
          showApiKeyButton: false,
        };
      default:
        return {
          title: "Something Went Wrong",
          message: error.message,
          showApiKeyButton: false,
        };
    }
  };

  const { title, message, showApiKeyButton } = getErrorContent();

  return (
    <div
      className={`rounded-lg border border-destructive/50 bg-destructive/10 p-4 max-w-md ${className}`}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
        <div className="flex-1 space-y-3">
          <div>
            <p className="text-sm font-medium text-destructive">{title}</p>
            <p className="text-sm text-destructive/80 mt-1">{message}</p>
          </div>

          {status === 429 && countdown !== null && countdown > 0 && (
            <p className="text-xs text-muted-foreground">
              Auto-retrying in {countdown}s...
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            {showApiKeyButton && (
              <Button
                variant="outline"
                size="sm"
                onClick={openApiKeySetup}
                className="gap-1.5 border-destructive/30 text-destructive hover:bg-destructive/10"
              >
                <Key className="h-3.5 w-3.5" />
                Update API Key
              </Button>
            )}
            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                disabled={status === 429 && countdown !== null && countdown > 0}
                className="gap-1.5 border-destructive/30 text-destructive hover:bg-destructive/10"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
