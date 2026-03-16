"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { Loader2, Download, Printer } from "lucide-react";

export default function ExportPage() {
  const { id } = useParams<{ id: string }>();
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .assessmentExport(id)
      .then(setMarkdown)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load export")
      )
      .finally(() => setLoading(false));
  }, [id]);

  const handleDownload = () => {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `assessment-${id.slice(0, 8)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-cyan" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  return (
    <>
      <style>{`@media print { .no-print { display: none !important; } body { background: white; color: black; } }`}</style>
      <div className="max-w-3xl mx-auto px-6 py-10">
        {/* Action bar — hidden when printing */}
        <div className="no-print flex gap-3 mb-8">
          <Button onClick={handleDownload} className="gap-2">
            <Download className="h-4 w-4" />
            Download .md
          </Button>
          <Button
            variant="outline"
            onClick={() => window.print()}
            className="gap-2"
          >
            <Printer className="h-4 w-4" />
            Print
          </Button>
        </div>

        {/* Report content */}
        <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-foreground">
          {markdown}
        </pre>
      </div>
    </>
  );
}
