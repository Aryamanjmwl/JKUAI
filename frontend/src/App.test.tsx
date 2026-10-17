// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("lets visitors retrieve source passages without entering a key", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ sources: [], exact_documents_used: [], latency_ms: 1 }) });
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  render(<App />);
  expect(screen.queryByLabelText("OpenAI API key")).toBeNull();
  await user.type(screen.getByLabelText("Your question"), "course requirements");
  await user.click(screen.getAllByRole("button", { name: "Search sources" })[1]);
  await waitFor(() => expect(fetch).toHaveBeenCalledOnce());
  expect(fetch.mock.calls[0][0]).toMatch(/\/search\/retrieval$/);
  expect(await screen.findByText("No matching source found", { selector: "h2" })).toBeTruthy();
});

it("requires a tab-scoped key only for the answer mode", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: "Answer with citations" }));
  expect(screen.getByLabelText("OpenAI API key")).toBeTruthy();
  expect(screen.queryByLabelText("Your question")).toBeNull();
  await user.type(screen.getByLabelText("OpenAI API key"), "sk-test");
  await user.click(screen.getByRole("button", { name: "Use this key" }));
  expect(screen.getByLabelText("Your question")).toBeTruthy();
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
  await user.click(screen.getByRole("button", { name: "Disconnect" }));
  expect(screen.getByLabelText("OpenAI API key")).toBeTruthy();
});
