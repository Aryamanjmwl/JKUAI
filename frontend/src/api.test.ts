import { afterEach, describe, expect, it, vi } from "vitest";
import { searchKnowledge, SearchError } from "./api";

const response = { sources: [], exact_documents_used: [], latency_ms: 1 };
afterEach(() => vi.unstubAllGlobals());

describe("search API", () => {
  it("searches sources without sending an OpenAI credential", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => response });
    vi.stubGlobal("fetch", fetch);
    const result = await searchKnowledge("course requirements", [], "secret", "retrieval");
    expect(fetch.mock.calls[0][0]).toMatch(/\/search\/retrieval$/);
    expect(fetch.mock.calls[0][1].headers).not.toHaveProperty("X-OpenAI-API-Key");
    expect(result.sources).toEqual([]);
  });

  it("passes the request key and simulated groups for answer generation", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...response, answer: "Answer. [S1]" }) });
    vi.stubGlobal("fetch", fetch);
    await searchKnowledge("course requirements", ["staff"], "secret");
    expect(fetch.mock.calls[0][0]).toMatch(/\/search$/);
    expect(fetch.mock.calls[0][1].headers).toMatchObject({ "X-OpenAI-API-Key": "secret", "X-User-Groups": "staff" });
  });

  it.each([401, 403, 429, 502, 422])("reports HTTP %s without exposing the response body", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status, json: async () => ({}) }));
    await expect(searchKnowledge("course requirements", [], "key")).rejects.toMatchObject({ name: "SearchError", status });
  });

  it("handles a connection failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("socket details")));
    await expect(searchKnowledge("course requirements", [], "key")).rejects.toBeInstanceOf(SearchError);
  });
});

describe("document upload API", () => {
  it("sends multipart fields without a manual boundary or provider key", async () => {
    const { uploadDocument } = await import("./api");
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ document_id: "id", chunks_created: 1, duplicate: false }) });
    vi.stubGlobal("fetch", fetch);
    await uploadDocument({ file: new File(["data"], "guide.pdf"), title: "Guide", sourceUrl: "https://example.org/guide.pdf", visibility: "restricted", allowedGroups: "staff" }, ["staff"]);
    const [url, request] = fetch.mock.calls[0];
    expect(url).toMatch(/\/documents$/);
    expect(request.headers).toEqual({ "X-User-Groups": "staff" });
    expect(request.body).toBeInstanceOf(FormData);
    expect(request.body.get("title")).toBe("Guide");
    expect(request.body.get("allowed_groups")).toBe("staff");
    expect(request.body.get("source_url")).toBe("https://example.org/guide.pdf");
  });

  it("returns a useful PDF validation message", async () => {
    const { uploadDocument } = await import("./api");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ detail: "No extractable text found in PDF" }) }));
    await expect(uploadDocument({ file: new File(["data"], "scan.pdf"), title: "Scan", sourceUrl: "", visibility: "public", allowedGroups: "" }, [])).rejects.toThrow("No extractable text");
  });
});

it.each([
  ["openai_quota_exhausted", "exhausted API credit"],
  ["openai_rate_limited", "temporarily rate-limited"],
])("distinguishes provider failure %s", async (code, message) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 429, json: async () => ({ detail: { code } }) }));
  await expect(searchKnowledge("question", [], "key")).rejects.toThrow(message);
});

it("routes Gemini credentials separately and labels its quota errors", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: false, status: 429, json: async () => ({ detail: { code: "gemini_rate_limited" } }) });
  vi.stubGlobal("fetch", fetch);
  await expect(searchKnowledge("question", [], "google-test", "answer", "gemini")).rejects.toThrow("free-tier quota");
  expect(fetch.mock.calls[0][1].headers).toMatchObject({ "X-Gemini-API-Key": "google-test" });
  expect(fetch.mock.calls[0][1].headers).not.toHaveProperty("X-OpenAI-API-Key");
});
