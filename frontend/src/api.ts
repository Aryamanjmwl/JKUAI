import type { SearchResult } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function searchKnowledge(query: string, groups: string[]): Promise<SearchResult> {
  const response = await fetch(`${API_URL}/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": "local-demo-user",
      "X-User-Groups": groups.join(","),
    },
    body: JSON.stringify({ query }),
  });
  if (!response.ok) {
    throw new Error(`Search failed (${response.status}): ${await response.text()}`);
  }
  return response.json() as Promise<SearchResult>;
}
