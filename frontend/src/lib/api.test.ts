import { vi } from "vitest";

// Mock the generated SDK functions
vi.mock("@/lib/generated/api-client", () => ({
  getSkillsApiSkillsGet: vi.fn(),
  gapAnalysisApiGapAnalysisPost: vi.fn(),
  learningPlanApiLearningPlanPost: vi.fn(),
}));

// Mock the client module
vi.mock("@/lib/generated/api-client/client.gen", () => ({
  client: { setConfig: vi.fn() },
}));

import { unwrap, api, ApiError, parseRetryAfter } from "./api";
import {
  getSkillsApiSkillsGet,
  gapAnalysisApiGapAnalysisPost,
  learningPlanApiLearningPlanPost,
} from "@/lib/generated/api-client";

const mockFetch = vi.fn();

beforeAll(() => {
  vi.stubGlobal("fetch", mockFetch);
});

afterAll(() => {
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe("parseRetryAfter", () => {
  it("returns undefined for null/undefined", () => {
    expect(parseRetryAfter(null)).toBeUndefined();
    expect(parseRetryAfter(undefined)).toBeUndefined();
  });

  it("returns undefined for empty string", () => {
    expect(parseRetryAfter("")).toBeUndefined();
  });

  it("parses numeric seconds string", () => {
    expect(parseRetryAfter("30")).toBe(30);
    expect(parseRetryAfter("0")).toBe(0);
    expect(parseRetryAfter("1.5")).toBe(2);
  });

  it("parses HTTP-date format", () => {
    const futureDate = new Date(Date.now() + 60_000).toUTCString();
    const result = parseRetryAfter(futureDate);
    expect(result).toBeGreaterThan(0);
    expect(result).toBeLessThanOrEqual(60);
  });

  it("returns undefined for past HTTP-date", () => {
    const pastDate = new Date(Date.now() - 60_000).toUTCString();
    expect(parseRetryAfter(pastDate)).toBeUndefined();
  });

  it("returns undefined for invalid string", () => {
    expect(parseRetryAfter("not-a-number-or-date")).toBeUndefined();
  });

  it("returns undefined for negative numbers", () => {
    expect(parseRetryAfter("-5")).toBeUndefined();
  });
});

describe("unwrap", () => {
  it("returns data on success", () => {
    expect(unwrap({ data: { id: 1 } })).toEqual({ id: 1 });
  });

  it("throws ApiError with detail message and status", () => {
    const mockResponse = { status: 404, headers: new Headers() } as Response;
    expect(() =>
      unwrap({ error: { detail: "Not found" }, response: mockResponse })
    ).toThrow("Not found");

    try {
      unwrap({ error: { detail: "Not found" }, response: mockResponse });
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
    }
  });

  it("throws ApiError with Retry-After header", () => {
    const headers = new Headers({ "Retry-After": "30" });
    const mockResponse = { status: 429, headers } as Response;
    try {
      unwrap({ error: { detail: "Rate limited" }, response: mockResponse });
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(429);
      expect((e as ApiError).retryAfter).toBe(30);
    }
  });

  it("throws generic message when no detail", () => {
    expect(() => unwrap({ error: {} })).toThrow("Request failed");
  });

  it("defaults to status 500 when no response", () => {
    try {
      unwrap({ error: { detail: "fail" } });
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(500);
    }
  });
});

describe("api.assessmentStart", () => {
  it("returns parsed response on success", async () => {
    const body = {
      sessionId: "abc",
      question: "What is React?",
      questionType: "open",
      step: 1,
      totalSteps: 3,
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(body),
    });

    const result = await api.assessmentStart(["s1"]);
    expect(result).toEqual(body);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/assessment/start"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("sends skillIds and targetLevel in body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ sessionId: "x", question: "Q", questionType: "o", step: 1, totalSteps: 1 }),
    });

    await api.assessmentStart(["s1", "s2"], "senior");

    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(callBody).toEqual({ skillIds: ["s1", "s2"], targetLevel: "senior" });
  });

  it("sends undefined targetLevel when omitted", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ sessionId: "x", question: "Q", questionType: "o", step: 1, totalSteps: 1 }),
    });

    await api.assessmentStart(["s1"]);

    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(callBody.skillIds).toEqual(["s1"]);
    expect(callBody.targetLevel).toBeUndefined();
  });

  it("throws ApiError on server error with detail and status", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers(),
      json: () => Promise.resolve({ detail: "Internal error" }),
    });

    try {
      await api.assessmentStart(["s1"]);
      expect.fail("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).message).toBe("Internal error");
      expect((e as ApiError).status).toBe(500);
    }
  });

  it("throws ApiError with Retry-After on 429", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 429,
      headers: new Headers({ "Retry-After": "60" }),
      json: () => Promise.resolve({ detail: "Rate limited" }),
    });

    try {
      await api.assessmentStart(["s1"]);
      expect.fail("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(429);
      expect((e as ApiError).retryAfter).toBe(60);
    }
  });

  it("throws fallback message on unparseable error JSON", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers(),
      json: () => Promise.reject(new Error("bad json")),
    });

    await expect(api.assessmentStart(["s1"])).rejects.toThrow(
      "Request failed"
    );
  });
});

describe("api.assessmentRespond", () => {
  it("calls correct URL with correct method and body", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true });

    await api.assessmentRespond("sess-123", "My answer");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/assessment/sess-123/respond"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ response: "My answer" }),
      })
    );
  });
});

describe("api.assessmentReport", () => {
  it("returns parsed report on success", async () => {
    const report = { proficiencyScores: [], knowledgeGraph: { nodes: [] }, gapNodes: [], learningPlan: { summary: "", totalHours: 0, phases: [] } };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(report),
    });

    const result = await api.assessmentReport("sess-123");
    expect(result).toEqual(report);
  });

  it("throws ApiError on error with detail and status", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      headers: new Headers(),
      json: () => Promise.resolve({ detail: "Not found" }),
    });

    try {
      await api.assessmentReport("bad");
      expect.fail("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
      expect((e as ApiError).message).toBe("Not found");
    }
  });

  it("throws fallback message on unparseable error JSON", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers(),
      json: () => Promise.reject(new Error("bad json")),
    });

    await expect(api.assessmentReport("bad")).rejects.toThrow(
      "Request failed"
    );
  });
});

describe("SDK-wrapped methods", () => {
  // SDK functions return { data, request, response } — we only care about data in unwrap()
  const sdkResult = (data: unknown) =>
    ({ data, request: {}, response: {} }) as never;

  it("getSkills unwraps SDK result", async () => {
    const data = { skills: [], categories: [] };
    vi.mocked(getSkillsApiSkillsGet).mockResolvedValueOnce(sdkResult(data));

    const result = await api.getSkills();
    expect(result).toEqual(data);
  });

  it("gapAnalysis unwraps SDK result", async () => {
    const data = { overallReadiness: 80, summary: "Good", gaps: [] };
    vi.mocked(gapAnalysisApiGapAnalysisPost).mockResolvedValueOnce(
      sdkResult(data)
    );

    const result = await api.gapAnalysis([]);
    expect(result).toEqual(data);
  });

  it("learningPlan unwraps SDK result", async () => {
    const data = {
      title: "Plan",
      summary: "s",
      totalHours: 10,
      totalWeeks: 2,
      phases: [],
    };
    vi.mocked(learningPlanApiLearningPlanPost).mockResolvedValueOnce(
      sdkResult(data)
    );

    const result = await api.learningPlan({
      overallReadiness: 80,
      summary: "s",
      gaps: [],
    });
    expect(result).toEqual(data);
  });

  it("getSkills propagates error through unwrap", async () => {
    vi.mocked(getSkillsApiSkillsGet).mockResolvedValueOnce(
      { error: { detail: "Unauthorized" }, request: {}, response: {} } as never
    );

    await expect(api.getSkills()).rejects.toThrow("Unauthorized");
  });

});

describe("api.assessmentExport", () => {
  it("calls GET /api/assessment/{id}/export", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve("# Assessment Report"),
    });

    await api.assessmentExport("sess-123");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/assessment/sess-123/export"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("returns text string on 200", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve("# Assessment Report\n*Generated by OpenLearning*"),
    });

    const result = await api.assessmentExport("sess-123");
    expect(result).toBe("# Assessment Report\n*Generated by OpenLearning*");
  });

  it("throws ApiError with detail on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      headers: new Headers(),
      json: () => Promise.resolve({ detail: "Session not found" }),
    });

    try {
      await api.assessmentExport("bad-id");
      expect.fail("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
      expect((e as ApiError).message).toBe("Session not found");
    }
  });

  it("throws fallback message when error body is not JSON", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers(),
      json: () => Promise.reject(new Error("bad json")),
    });

    await expect(api.assessmentExport("bad-id")).rejects.toThrow("Request failed");
  });
});
