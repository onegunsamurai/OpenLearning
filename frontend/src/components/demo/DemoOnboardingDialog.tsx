"use client";

import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

interface DemoOnboardingDialogProps {
  open: boolean;
  onDismiss: () => void;
}

export function DemoOnboardingDialog({
  open,
  onDismiss,
}: DemoOnboardingDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onDismiss()}>
      <DialogContent className="max-w-md p-6 sm:p-8">
        <DialogTitle className="text-xl">
          You&apos;re in Demo Mode
        </DialogTitle>
        <DialogDescription className="sr-only">
          Information about the demo experience
        </DialogDescription>

        <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
          <li className="flex items-start gap-2.5">
            <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" />
            Responses are scripted — type anything to advance
          </li>
          <li className="flex items-start gap-2.5">
            <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" />
            No API key or account required
          </li>
          <li className="flex items-start gap-2.5">
            <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" />
            You&apos;ll see a sample gap analysis and learning plan at the end
          </li>
        </ul>

        <Button
          onClick={onDismiss}
          className="mt-6 w-full bg-cyan text-background hover:bg-cyan/90 font-semibold gap-2 h-11"
        >
          Start Demo
          <ArrowRight className="h-4 w-4" />
        </Button>
      </DialogContent>
    </Dialog>
  );
}
