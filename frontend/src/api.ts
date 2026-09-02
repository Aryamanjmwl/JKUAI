import type { SearchResult } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function searchKnowledge(query: string, groups: string[]): Promise<SearchResult> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": "local-demo-user",
        "X-User-Groups": groups.join(","),
      },
      body: JSON.stringify({ query }),
    });
  } catch {
    throw new Error("The search service is not available right now. Please try again in a moment.");
  }
  if (!response.ok) {
    if (response.status === 403) {
      throw new Error("You don't have access to the documents needed for this question.");
    }
    if (response.status >= 500) {
      throw new Error("The search service is temporarily unavailable. Please try again in a moment.");
    }
    throw new Error("We couldn't understand that request. Please rephrase your question.");
  }
  return response.json() as Promise<SearchResult>;
}
