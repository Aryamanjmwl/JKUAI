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
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status }));
    await expect(searchKnowledge("course requirements", [], "key")).rejects.toMatchObject({ name: "SearchError", status });
  });

  it("handles a connection failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("socket details")));
    await expect(searchKnowledge("course requirements", [], "key")).rejects.toBeInstanceOf(SearchError);
  });
});
