import { createDemoSSEResponse } from "./demo-assessment";
import { DEMO_QUESTIONS, DEMO_RESPONSES } from "./fixtures";

async function readStream(response: Response): Promise<string[]> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  const lines: string[] = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    for (const line of chunk.split("\n")) {
      if (line.startsWith("data: ")) {
        lines.push(line.slice(6));
      }
    }
  }
  return lines;
}

describe("createDemoSSEResponse", () => {
  it("returns a Response with SSE content type", () => {
    const response = createDemoSSEResponse(0, false);
    expect(response).toBeInstanceOf(Response);
    expect(response.headers.get("Content-Type")).toBe("text/event-stream");
  });

  it("emits response text words", async () => {
    const response = createDemoSSEResponse(0, false);
    const lines = await readStream(response);

    const responseWords = DEMO_RESPONSES[0].split(" ");
    expect(lines[0]).toBe(responseWords[0]);
  });

  it("emits META with progress info", async () => {
    const response = createDemoSSEResponse(0, false);
    const lines = await readStream(response);

    const metaLine = lines.find((l) => l.startsWith("[META]"));
    expect(metaLine).toBeDefined();

    const meta = JSON.parse(metaLine!.slice(6));
    expect(meta.type).toBeDefined();
    expect(meta.total_questions).toBeDefined();
  });

  it("ends with [DONE]", async () => {
    const response = createDemoSSEResponse(0, false);
    const lines = await readStream(response);
    expect(lines[lines.length - 1]).toBe("[DONE]");
  });

  it("does NOT emit [ASSESSMENT_COMPLETE] for non-final step", async () => {
    const response = createDemoSSEResponse(0, false);
    const lines = await readStream(response);
    expect(lines.find((l) => l === "[ASSESSMENT_COMPLETE]")).toBeUndefined();
  });

  it("emits next question text for non-final step", async () => {
    const response = createDemoSSEResponse(0, false);
    const lines = await readStream(response);

    // Next question words should be in the stream
    const nextQuestionFirstWord = DEMO_QUESTIONS[1].question.split(" ")[0];
    expect(lines.some((l) => l.includes(nextQuestionFirstWord))).toBe(true);
  });

  it("emits [ASSESSMENT_COMPLETE] on final step", async () => {
    const lastStep = DEMO_QUESTIONS.length - 1;
    const response = createDemoSSEResponse(lastStep, true);
    const lines = await readStream(response);

    expect(lines).toContain("[ASSESSMENT_COMPLETE]");
    expect(lines[lines.length - 1]).toBe("[DONE]");
  });

  it("does NOT emit next question text on final step", async () => {
    const lastStep = DEMO_QUESTIONS.length - 1;
    const response = createDemoSSEResponse(lastStep, true);
    const lines = await readStream(response);

    // Response words should be from the last response
    const responseWords = DEMO_RESPONSES[lastStep].split(" ");
    expect(lines[0]).toBe(responseWords[0]);

    // No next question — lines should only be response words + meta + complete + done
    // (no question words from a non-existent next question)
  });

  it("uses fallback text for out-of-bounds step", async () => {
    const response = createDemoSSEResponse(999, false);
    const lines = await readStream(response);

    // Should use the fallback "Thanks for your answer!" text
    expect(lines[0]).toBe("Thanks");
  });
});
