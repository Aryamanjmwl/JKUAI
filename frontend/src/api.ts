import type { SearchResult } from "./types";

export type AnswerProvider = "openai" | "gemini";

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
  apiKey: string,
  mode: "answer" | "retrieval" = "answer",
  provider: AnswerProvider = "openai",
): Promise<SearchResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (mode === "answer") {
    headers[provider === "gemini" ? "X-Gemini-API-Key" : "X-OpenAI-API-Key"] = apiKey;
  }
  const providerName = provider === "gemini" ? "Gemini" : "OpenAI";
  if (groups.length > 0) {
    headers["X-User-Id"] = "local-demo-user";
    headers["X-User-Groups"] = groups.join(",");
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}/search${mode === "retrieval" ? "/retrieval" : ""}`, {
      method: "POST",
      headers,
      body: JSON.stringify(mode === "answer" ? { query, provider } : { query }),
    });
  } catch {
    throw new SearchError(
      "The search service is not available right now. Please try again in a moment.",
    );
  }
  if (!response.ok) {
    if (response.status === 401) {
      throw new SearchError(
        `${providerName} did not accept that key. Check the selected provider and copied key, then try again.`,
        response.status,
      );
    }
    if (response.status === 429) {
      const body = await response.json().catch(() => ({})) as { detail?: { code?: string } };
      const code = body.detail?.code;
      throw new SearchError(
        code === `${provider}_quota_exhausted`
          ? `${providerName} reports exhausted API credit or a billing limit for this key's project. Check API billing or change your API key.`
          : code === `${provider}_rate_limited`
            ? provider === "gemini"
              ? "Gemini reached a rate or free-tier quota limit. Wait before retrying and check your limits in Google AI Studio. Changing keys in the same project does not reset quota."
              : "OpenAI temporarily rate-limited this request. Wait a moment before trying again."
            : `${providerName} rejected this request with a rate or usage limit. Check the provider dashboard for your project's limits.`,
        response.status,
      );
    }
    if (response.status === 403) {
      const body = await response.json().catch(() => ({})) as { detail?: { code?: string } };
      if (body.detail?.code === "provider_access_denied") {
        throw new SearchError(`${providerName} denied API access. Check key restrictions, project API access, and supported region in the provider dashboard.`, response.status);
      }
      throw new SearchError(
        "You don't have access to the documents needed for this question.",
        response.status,
      );
    }
    if (response.status >= 500) {
      const body = await response.json().catch(() => ({})) as { detail?: { code?: string } };
      if (body.detail?.code === "provider_configuration_error") {
        throw new SearchError(`${providerName} rejected the configured model or request. Check the server's model setting and model access.`, response.status);
      }
      if (body.detail?.code === "provider_unavailable") {
        throw new SearchError(`${providerName} could not complete the request. Please try again later.`, response.status);
      }
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
  return { ...result, answer: result.answer ?? "These are retrieved passages, not a generated answer. Connect an API key to get an answer with source tags." };
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
