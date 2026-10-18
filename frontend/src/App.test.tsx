// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const sources = [{ citation_id: "S1", chunk_id: "chunk", title: "Guide", excerpt: "Contact office@example.org", page_number: 1 }];
const result = { answer: "Contact office@example.org [S1]", sources, exact_documents_used: ["Guide"], latency_ms: 1 };

it("uses one question flow and shows sources without a key", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...result, answer: undefined }) });
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  render(<App />);
  expect(screen.queryByRole("button", { name: "Search sources" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Answer with citations" })).toBeNull();
  await user.type(screen.getByLabelText("Your question"), "course requirements");
  await user.click(screen.getByRole("button", { name: "Ask JKUAI" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledOnce());
  expect(fetch.mock.calls[0][0]).toMatch(/\/search\/retrieval$/);
  expect(await screen.findByRole("link", { name: "[S1]" })).toBeTruthy();
});

it("replaces a tab-scoped key and submits the new key with cited answers", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => result });
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  render(<App />);
  await user.selectOptions(screen.getByLabelText("Answer provider"), "openai");
  await user.type(screen.getByLabelText("OpenAI API key"), "sk-old");
  await user.click(screen.getByRole("button", { name: "Use this key" }));
  await user.type(screen.getByLabelText("Your question"), "contact email");
  await user.click(screen.getByRole("button", { name: "Change API key" }));
  expect((screen.getByLabelText("OpenAI API key") as HTMLInputElement).value).toBe("");
  await user.type(screen.getByLabelText("OpenAI API key"), "sk-new");
  await user.click(screen.getByRole("button", { name: "Use this key" }));
  await user.click(screen.getByRole("button", { name: "Ask JKUAI" }));
  await screen.findByText("Based on retrieved documents");
  expect(fetch.mock.calls[0][1].headers["X-OpenAI-API-Key"]).toBe("sk-new");
  expect(screen.getAllByRole("link", { name: /S1/ }).length).toBe(2);
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
  await user.click(screen.getByRole("button", { name: "Disconnect" }));
  expect(screen.getByLabelText("OpenAI API key")).toBeTruthy();
});

it("keeps sources and the question when generation fails and allows changing keys", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce({ ok: false, status: 429, json: async () => ({ detail: { code: "openai_quota_exhausted" } }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...result, answer: undefined }) });
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  render(<App />);
  await user.selectOptions(screen.getByLabelText("Answer provider"), "openai");
  await user.type(screen.getByLabelText("OpenAI API key"), "sk-test");
  await user.click(screen.getByRole("button", { name: "Use this key" }));
  await user.type(screen.getByLabelText("Your question"), "contact email");
  await user.click(screen.getByRole("button", { name: "Ask JKUAI" }));
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("exhausted API credit"));
  expect(await screen.findByText("Retrieved source passages")).toBeTruthy();
  expect(screen.getByText("Contact office@example.org")).toBeTruthy();
  expect(fetch.mock.calls[1][1].headers).not.toHaveProperty("X-OpenAI-API-Key");
  expect(screen.getByRole("button", { name: "Change API key" })).toBeTruthy();
});

it("defaults to Gemini and clears its credential when switching providers", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => result });
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("Gemini API key"), "google-test");
  await user.click(screen.getByRole("button", { name: "Use this key" }));
  await user.type(screen.getByLabelText("Your question"), "contact email");
  await user.click(screen.getByRole("button", { name: "Ask JKUAI" }));
  await screen.findByText("Based on retrieved documents");
  expect(fetch.mock.calls[0][1].headers["X-Gemini-API-Key"]).toBe("google-test");
  expect(fetch.mock.calls[0][1].headers).not.toHaveProperty("X-OpenAI-API-Key");
  expect(JSON.parse(fetch.mock.calls[0][1].body).provider).toBe("gemini");
  await user.click(screen.getByRole("button", { name: "Change API key" }));
  await user.selectOptions(screen.getByLabelText("Answer provider"), "openai");
  expect((screen.getByLabelText("OpenAI API key") as HTMLInputElement).value).toBe("");
  expect(screen.queryByText("Based on retrieved documents")).toBeNull();
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});
