import { type FormEvent, useState } from "react";

import { searchKnowledge } from "./api";
import type { SearchResult } from "./types";

const EXAMPLE_QUERY = "Which courses do I need before taking Advanced Machine Learning?";

export default function App() {
  const [query, setQuery] = useState(EXAMPLE_QUERY);
  const [group, setGroup] = useState("students");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length < 3) return;
    setLoading(true);
    setError("");
    try {
      setResult(await searchKnowledge(query.trim(), group ? [group] : []));
    } catch (reason) {
      setResult(null);
      setError(reason instanceof Error ? reason.message : "Search failed unexpectedly.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header>
        <a className="brand" href="/" aria-label="JKUAI home">
          <span className="mark">J</span><span>JKUAI</span>
        </a>
        <span className="environment">Knowledge Search</span>
      </header>

      <section className="hero">
        <p className="eyebrow">Grounded university intelligence</p>
        <h1>Answers you can verify.</h1>
        <p className="intro">
          Search course descriptions, regulations, FAQs, and study documents with document-level
          permissions and precise source attribution.
        </p>
        <form onSubmit={submit}>
          <label htmlFor="query">Ask a question</label>
          <div className="search-row">
            <input
              id="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask about courses, prerequisites, or regulations…"
            />
            <button disabled={loading} type="submit">{loading ? "Searching…" : "Search"}</button>
          </div>
          <div className="access-row">
            <span>Access context</span>
            <select value={group} onChange={(event) => setGroup(event.target.value)}>
              <option value="">Public only</option>
              <option value="students">Student</option>
              <option value="staff">Staff</option>
              <option value="admissions">Admissions</option>
            </select>
            <small>Development identity adapter</small>
          </div>
        </form>
      </section>

      {error && <div className="error" role="alert">{error}</div>}

      {result && (
        <section className="result-grid" aria-live="polite">
          <article className="answer-card">
            <div className="card-heading">
              <h2>Answer</h2><span>{Math.round(result.latency_ms)} ms</span>
            </div>
            <p className="answer">{result.answer}</p>
            <div className="documents">
              <h3>Exact documents used</h3>
              <ul>{result.exact_documents_used.map((name) => <li key={name}>{name}</li>)}</ul>
            </div>
          </article>

          <aside className="sources">
            <h2>Sources</h2>
            {result.sources.map((source) => (
              <article id={source.citation_id} key={source.chunk_id} className="source-card">
                <div className="source-meta">
                  <strong>[{source.citation_id}]</strong>
                  <span>{source.page_number ? `Page ${source.page_number}` : "Page unavailable"}</span>
                </div>
                <h3>{source.title}</h3>
                <p>{source.excerpt}</p>
                {source.source_url && (
                  <a href={source.source_url} target="_blank" rel="noreferrer">Open document ↗</a>
                )}
              </article>
            ))}
          </aside>
        </section>
      )}
    </main>
  );
}
