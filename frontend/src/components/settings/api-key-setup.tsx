"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Eye, EyeOff, Loader2, Check, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";

interface ApiKeySetupProps {
  open: boolean;
  onClose: () => void;
  onKeySet?: () => void;
}

type Status = "idle" | "validating" | "success" | "error";

/**
 * Wrapper that conditionally renders the dialog content,
 * so state resets naturally on each open via remount.
 */
export function ApiKeySetup({ open, onClose, onKeySet }: ApiKeySetupProps) {
  if (!open) return null;
  return <ApiKeySetupInner onClose={onClose} onKeySet={onKeySet} />;
}

function ApiKeySetupInner({ onClose, onKeySet }: Omit<ApiKeySetupProps, "open">) {
  const [keyInput, setKeyInput] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const fetchPreview = useCallback(() => {
    api
      .authGetApiKey()
      .then((res) => setPreview(res?.apiKeyPreview ?? null))
      .catch(() => setPreview(null));
  }, []);

  useEffect(() => {
    fetchPreview();
  }, [fetchPreview]);

  const handleValidateAndSave = async () => {
    if (!keyInput.trim()) return;
    setStatus("validating");
    setErrorMessage("");

    try {
      const result = await api.authValidateKey(keyInput.trim());
      if (!result.valid) {
        setStatus("error");
        setErrorMessage(result.error ?? "Invalid API key");
        return;
      }
    } catch {
      setStatus("error");
      setErrorMessage("Failed to validate key");
      return;
    }

    try {
      await api.authSetApiKey(keyInput.trim());
      setStatus("success");
      timerRef.current = setTimeout(() => {
        onKeySet?.();
        onClose();
      }, 800);
    } catch {
      setStatus("error");
      setErrorMessage("Key is valid but failed to save. Please try again.");
    }
  };

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await api.authDeleteApiKey();
      setPreview(null);
      onKeySet?.();
      onClose();
    } catch {
      setRemoving(false);
    }
  };

  return (
    <Dialog open onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-md p-8">
        <DialogClose
          className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </DialogClose>
        <DialogTitle className="text-xl">Set Up Your API Key</DialogTitle>
        <DialogDescription className="mt-1 text-sm text-muted-foreground">
          Enter your Anthropic API key to power assessments. Get one at{" "}
          <a
            href="https://console.anthropic.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan underline underline-offset-2"
          >
            console.anthropic.com
          </a>
        </DialogDescription>

        {preview && (
          <div className="mt-4 flex items-center justify-between rounded-lg border border-border bg-secondary px-4 py-3">
            <div>
              <p className="text-xs text-muted-foreground">Current key</p>
              <p className="font-mono text-sm">{preview}</p>
            </div>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleRemove}
              disabled={removing}
              aria-label="Remove API key"
            >
              {removing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4 text-destructive" />
              )}
            </Button>
          </div>
        )}

        <div className="mt-4 space-y-3">
          <div className="relative">
            <Input
              type={showKey ? "text" : "password"}
              placeholder="sk-ant-..."
              value={keyInput}
              onChange={(e) => {
                setKeyInput(e.target.value);
                if (status === "error") setStatus("idle");
              }}
              className="pr-10"
              aria-label="API key"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label={showKey ? "Hide API key" : "Show API key"}
            >
              {showKey ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>

          {status === "error" && errorMessage && (
            <p className="text-sm text-destructive">{errorMessage}</p>
          )}

          <Button
            onClick={handleValidateAndSave}
            disabled={!keyInput.trim() || status === "validating" || status === "success"}
            className="w-full bg-cyan text-background hover:bg-cyan/90 font-semibold h-11"
          >
            {status === "validating" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Validating...
              </>
            ) : status === "success" ? (
              <>
                <Check className="mr-2 h-4 w-4" />
                Saved!
              </>
            ) : preview ? (
              "Update Key"
            ) : (
              "Validate & Save"
            )}
          </Button>
          <button
            type="button"
            onClick={onClose}
            className="w-full text-center text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Skip for now
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
