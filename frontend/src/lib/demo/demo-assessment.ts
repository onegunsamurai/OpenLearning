import { DEMO_QUESTIONS, DEMO_RESPONSES } from "./fixtures";

/**
 * Creates a synthetic SSE Response that mirrors the backend's streaming format.
 * The `useAssessmentChat` hook reads `response.body.getReader()` and parses
 * `data:` lines, so we produce the exact same format here.
 */
export function createDemoSSEResponse(
  demoStep: number,
  isFinal: boolean
): Response {
  const responseText = DEMO_RESPONSES[demoStep] ?? "Thanks for your answer!";

  // If there's a next question, append it after the response
  const nextQuestion = !isFinal ? DEMO_QUESTIONS[demoStep + 1] : undefined;
  const meta = nextQuestion?.meta ?? DEMO_QUESTIONS[demoStep]?.meta;

  const words = responseText.split(" ");
  const nextQuestionWords = nextQuestion
    ? ["\n\n", ...nextQuestion.question.split(" ")]
    : [];

  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      // Emit the response text word-by-word
      for (let i = 0; i < words.length; i++) {
        const prefix = i === 0 ? "" : " ";
        const data = `data: ${prefix}${words[i]}\n\n`;
        controller.enqueue(encoder.encode(data));
        await delay(30 + Math.random() * 20);
      }

      // Emit META with progress info
      if (meta) {
        const metaPayload = `data: [META]${JSON.stringify(meta)}\n\n`;
        controller.enqueue(encoder.encode(metaPayload));
        await delay(50);
      }

      // If final question, emit ASSESSMENT_COMPLETE
      if (isFinal) {
        controller.enqueue(encoder.encode("data: [ASSESSMENT_COMPLETE]\n\n"));
        await delay(50);
      }

      // Emit next question text if not final
      if (nextQuestionWords.length > 0) {
        for (let i = 0; i < nextQuestionWords.length; i++) {
          const prefix = i <= 1 ? "" : " ";
          const data = `data: ${prefix}${nextQuestionWords[i]}\n\n`;
          controller.enqueue(encoder.encode(data));
          await delay(30 + Math.random() * 20);
        }
      }

      // End the stream
      controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      controller.close();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
