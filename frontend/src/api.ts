import type { SearchResult } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class SearchError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "SearchError";
  }
}

export async function searchKnowledge(
  query: string,
  groups: string[],
  openaiApiKey: string,
  mode: "answer" | "retrieval" = "answer",
): Promise<SearchResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (mode === "answer") headers["X-OpenAI-API-Key"] = openaiApiKey;
  if (groups.length > 0) {
    headers["X-User-Id"] = "local-demo-user";
    headers["X-User-Groups"] = groups.join(",");
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}/search${mode === "retrieval" ? "/retrieval" : ""}`, {
      method: "POST",
      headers,
      body: JSON.stringify({ query }),
    });
  } catch {
    throw new SearchError(
      "The search service is not available right now. Please try again in a moment.",
    );
  }
  if (!response.ok) {
    if (response.status === 401) {
      throw new SearchError(
        "OpenAI didn't accept that key. Check that you copied the full key, then try again.",
        response.status,
      );
    }
    if (response.status === 429) {
      throw new SearchError(
        "This OpenAI account has reached a rate or spending limit. Check its API billing and usage, then try again.",
        response.status,
      );
    }
    if (response.status === 403) {
      throw new SearchError(
        "You don't have access to the documents needed for this question.",
        response.status,
      );
    }
    if (response.status >= 500) {
      throw new SearchError(
        "The search service is temporarily unavailable. Please try again in a moment.",
        response.status,
      );
    }
    throw new SearchError(
      "We couldn't understand that request. Please rephrase your question.",
      response.status,
    );
  }
  const result = await response.json() as SearchResult;
  return { ...result, answer: result.answer ?? "Explore the ranked passages below. Choose Answer with citations to generate a response from these sources." };
}

export async function uploadDocument(
  document: { file: File; title: string; sourceUrl: string; visibility: string; allowedGroups: string },
  groups: string[],
) {
  const body = new FormData();
  body.set("file", document.file);
  body.set("title", document.title);
  body.set("visibility", document.visibility);
  body.set("allowed_groups", document.allowedGroups);
  if (document.sourceUrl) body.set("source_url", document.sourceUrl);
  const headers: Record<string, string> = {};
  if (groups.length) headers["X-User-Groups"] = groups.join(",");
  let response: Response;
  try {
    response = await fetch(`${API_URL}/documents`, { method: "POST", headers, body });
  } catch {
    throw new Error("Cannot reach the document service. Check that the app is running and try again.");
  }
  if (!response.ok) {
    if (response.status === 409) throw new Error("This PDF already exists with different access settings, or your current role cannot access it. Use its original access settings and an authorized role.");
    if (response.status === 413) throw new Error("The PDF exceeds the upload size limit.");
    if (response.status === 400 || response.status === 422) {
      const error = await response.json().catch(() => ({})) as { detail?: unknown };
      throw new Error(typeof error.detail === "string" ? error.detail : "Check the PDF and document details, then try again.");
    }
    throw new Error("The document could not be indexed. Check the services and try again.");
  }
  return response.json() as Promise<import("./types").IngestResult>;
}
