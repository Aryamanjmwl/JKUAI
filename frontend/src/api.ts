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
): Promise<SearchResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-OpenAI-API-Key": openaiApiKey,
  };
  if (groups.length > 0) {
    headers["X-User-Id"] = "local-demo-user";
    headers["X-User-Groups"] = groups.join(",");
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}/search`, {
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
  return response.json() as Promise<SearchResult>;
}
