import { type FormEvent, useState } from "react";

import { searchKnowledge } from "./api";
import type { SearchResult, Source } from "./types";

const EXAMPLE_QUESTIONS = [
  "What do I need before taking Advanced Machine Learning?",
  "How many ECTS credits do I need to graduate?",
  "What happens if I miss an exam?",
];

function AnswerText({ answer, sources }: { answer: string; sources: Source[] }) {
  const sourceIds = new Set(sources.map((source) => source.citation_id));

  return answer.split(/(\[S\d+\])/g).map((part, index) => {
    const citationId = part.match(/^\[(S\d+)\]$/)?.[1];
    if (!citationId || !sourceIds.has(citationId)) {
      return <span key={`${part}-${index}`}>{part}</span>;
    }
    return (
      <a className="citation" href={`#${citationId}`} key={`${citationId}-${index}`}>
        {part}
        <span className="sr-only"> Go to source {citationId.slice(1)}</span>
      </a>
    );
  });
}

export default function App() {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("students");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function runSearch(question: string) {
    const cleanQuestion = question.trim();
    if (cleanQuestion.length < 3 || loading) return;

    setQuery(cleanQuestion);
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await searchKnowledge(cleanQuestion, group ? [group] : []));
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "We couldn't complete your search. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void runSearch(query);
  }

  const sourceCount = result?.sources.length ?? 0;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="JKU Knowledge Search home">
          <span className="brand-mark" aria-hidden="true">J</span>
          <span className="brand-copy">
            <strong>JKU Knowledge Search</strong>
            <small>Student information, with sources</small>
          </span>
        </a>

        <div className="role-picker">
          <label htmlFor="role">Viewing as</label>
          <select id="role" value={group} onChange={(event) => setGroup(event.target.value)}>
            <option value="students">Student</option>
            <option value="">Public visitor</option>
            <option value="staff">Staff member</option>
            <option value="admissions">Admissions team</option>
          </select>
        </div>
      </header>

      <main>
        <section className="search-section" aria-labelledby="page-title">
          <p className="section-label">JKU STUDY INFORMATION</p>
          <h1 id="page-title">What would you like to know?</h1>
          <p className="intro">
            Ask about courses, prerequisites, exams, deadlines, or university regulations.
            Every answer shows the documents it came from.
          </p>

          <form className="search-form" onSubmit={submit}>
            <label className="sr-only" htmlFor="question">Your question</label>
            <div className="question-box">
              <textarea
                id="question"
                rows={2}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="For example: Which courses do I need before Advanced Machine Learning?"
                aria-describedby="question-help"
              />
              <button disabled={loading || query.trim().length < 3} type="submit">
                {loading ? "Searching…" : "Ask JKUAI"}
              </button>
            </div>
            <p id="question-help" className="question-help">Press Enter to search · Shift + Enter for a new line</p>
          </form>

          <div className="examples" aria-label="Example questions">
            <span>Try an example</span>
            <div className="example-list">
              {EXAMPLE_QUESTIONS.map((example) => (
                <button key={example} disabled={loading} onClick={() => void runSearch(example)} type="button">
                  {example}
                </button>
              ))}
            </div>
          </div>
        </section>

        {loading && (
          <section className="status-card" role="status" aria-live="polite">
            <span className="spinner" aria-hidden="true" />
            <div>
              <strong>Searching JKU documents…</strong>
              <p>Checking relevant courses, regulations, and study information.</p>
            </div>
          </section>
        )}

        {error && (
          <section className="error-card" role="alert">
            <div>
              <strong>We couldn’t complete that search.</strong>
              <p>{error}</p>
            </div>
            <button onClick={() => void runSearch(query)} type="button">Try again</button>
          </section>
        )}

        {!loading && !error && !result && (
          <section className="how-it-works" aria-label="How search works">
            <div><span>1</span><p><strong>Ask naturally</strong>Use the same words you would use when asking a study advisor.</p></div>
            <div><span>2</span><p><strong>Read the answer</strong>JKUAI combines information found in relevant documents.</p></div>
            <div><span>3</span><p><strong>Check the sources</strong>Open the exact documents and pages used for the answer.</p></div>
          </section>
        )}

        {result && (
          <section className="results" aria-live="polite">
            <article className="answer-panel">
              <div className="panel-heading">
                <div>
                  <p className="section-label">ANSWER</p>
                  <h2>{sourceCount > 0 ? "Based on JKU documents" : "No verified answer found"}</h2>
                </div>
                <span className="source-count">{sourceCount} {sourceCount === 1 ? "source" : "sources"}</span>
              </div>

              <p className="answer-text">
                <AnswerText answer={result.answer} sources={result.sources} />
              </p>

              {sourceCount > 0 && (
                <div className="verification-note">
                  <span aria-hidden="true">✓</span>
                  <p><strong>Easy to verify</strong>Select a citation in the answer or open a source document to check the information.</p>
                </div>
              )}

              {result.exact_documents_used.length > 0 && (
                <details className="documents-used">
                  <summary>Documents used in this answer ({result.exact_documents_used.length})</summary>
                  <ul>
                    {result.exact_documents_used.map((name) => <li key={name}>{name}</li>)}
                  </ul>
                </details>
              )}
            </article>

            <aside className="sources-panel" aria-label="Sources used">
              <div className="sources-heading">
                <div>
                  <p className="section-label">SOURCES</p>
                  <h2>Where this answer came from</h2>
                </div>
                <span>{Math.round(result.latency_ms) / 1000}s</span>
              </div>

              {sourceCount === 0 ? (
                <div className="no-sources">
                  <strong>No matching source found</strong>
                  <p>Try using the official course name or asking a more specific question.</p>
                </div>
              ) : (
                <div className="source-list">
                  {result.sources.map((source, index) => (
                    <article id={source.citation_id} key={source.chunk_id} className="source-card">
                      <div className="source-meta">
                        <span className="source-number">{index + 1}</span>
                        <span>{source.page_number ? `Page ${source.page_number}` : "Page not listed"}</span>
                      </div>
                      <h3>{source.title}</h3>
                      <p>{source.excerpt}</p>
                      {source.source_url && (
                        <a href={source.source_url} target="_blank" rel="noreferrer">
                          Open official document <span aria-hidden="true">↗</span>
                        </a>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </aside>
          </section>
        )}
      </main>

      <footer>
        <p>JKUAI may make mistakes. Confirm important requirements in the linked official documents.</p>
      </footer>
    </div>
  );
}
