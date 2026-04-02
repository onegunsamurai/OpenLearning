"use client";

import { memo } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

interface MarkdownBodyProps {
  content: string;
}

const REHYPE_PLUGINS = [rehypeSanitize];

export const MarkdownBody = memo(function MarkdownBody({
  content,
}: MarkdownBodyProps) {
  return (
    <div className="prose prose-sm prose-invert max-w-none text-muted-foreground [&_a]:text-cyan [&_a]:underline [&_strong]:text-foreground [&_code]:text-cyan [&_code]:bg-secondary [&_code]:px-1 [&_code]:rounded">
      <ReactMarkdown rehypePlugins={REHYPE_PLUGINS}>
        {content}
      </ReactMarkdown>
    </div>
  );
});
