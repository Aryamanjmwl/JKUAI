import { type FormEvent, useState } from "react";
import Markdown from "react-markdown";

import { type AnswerProvider, SearchError, searchKnowledge } from "./api";
import type { SearchResult, Source } from "./types";
import DocumentUpload from "./DocumentUpload";

const EXAMPLE_QUESTIONS = [
  "What do I need before taking Advanced Machine Learning?",
  "How many ECTS credits do I need to graduate?",
  "What happens if I miss an exam?",
];
const DEMO_ROLES_ENABLED = import.meta.env.VITE_ENABLE_DEMO_ROLES === "true";

function AnswerText({ answer, sources }: { answer: string; sources: Source[] }) {
  const sourceIds = new Set(sources.map((source) => source.citation_id));

  const markdown = answer.replace(/\[(S\d+)\]/g, (marker, id: string) =>
    sourceIds.has(id) ? `[${marker}](#${id})` : marker,
  );

  return (
    <Markdown
      skipHtml
      allowedElements={["p", "strong", "em", "ul", "ol", "li", "code", "pre", "blockquote", "a", "h2", "h3", "h4", "hr", "br"]}
      components={{
        a({ href, children }) {
          const id = href?.match(/^#(S\d+)$/)?.[1];
          if (!id || !sourceIds.has(id)) return <span>{children}</span>;
          return <a className="citation" href={`#${id}`}>
            {children}<span className="sr-only"> Go to source {id.slice(1)}</span>
          </a>;
        },
      }}
    >{markdown}</Markdown>
  );
}

export default function App() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [editingKey, setEditingKey] = useState(false);
  const [answerUnavailable, setAnswerUnavailable] = useState(false);
  const [provider, setProvider] = useState<AnswerProvider>("gemini");
  const providerName = provider === "gemini" ? "Gemini" : "OpenAI";
  const [apiKey, setApiKey] = useState("");
  const mode = apiKey ? "answer" : "retrieval";
  const [draftApiKey, setDraftApiKey] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState(DEMO_ROLES_ENABLED ? "students" : "");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function runSearch(question: string) {
    const cleanQuestion = question.trim();
    if (cleanQuestion.length < 3 || loading) return;

    setQuery(cleanQuestion);
    setLoading(true);
    setAnswerUnavailable(false);
    setError("");
    setResult(null);
    try {
      setResult(await searchKnowledge(cleanQuestion, group ? [group] : [], apiKey, mode, provider));
    } catch (reason) {
      setAnswerUnavailable(mode === "answer");
      // Keep accessible evidence visible even when the answer provider fails.
      if (mode === "answer") {
        try {
          setResult(await searchKnowledge(cleanQuestion, group ? [group] : [], "", "retrieval"));
        } catch { /* Preserve the original failure rather than replacing it. */ }
      }
      if (reason instanceof SearchError && reason.status === 401) {
        setApiKey("");
        setDraftApiKey("");
      }
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

  function connectProvider(event: FormEvent) {
    event.preventDefault();
    const cleanKey = draftApiKey.trim();
    if (!cleanKey) return;

    setApiKey(cleanKey);
    setEditingKey(false);
    setResult(null);
    setAnswerUnavailable(false);
    setDraftApiKey("");
    setShowApiKey(false);
    setError("");
  }

  function disconnectProvider() {
    setApiKey("");
    setEditingKey(false);
    setDraftApiKey("");
    setResult(null);
    setError("");
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

        <div className="topbar-actions">
          <button className="upload-toggle" type="button" aria-expanded={uploadOpen} aria-controls="document-upload" disabled={uploading} onClick={() => setUploadOpen((open) => !open)}>
            {uploadOpen ? "Close upload" : "Add PDF"}
          </button>
          {apiKey && (
            <div className="key-status" role="status">
              <span aria-hidden="true" />
              <span>{providerName} key set</span>
              <button disabled={loading} onClick={() => { setEditingKey(true); setDraftApiKey(""); setShowApiKey(false); }} type="button">Change API key</button>
              <button disabled={loading} onClick={disconnectProvider} type="button">Disconnect</button>
            </div>
          )}
        </div>
      </header>

      <main>
        {DEMO_ROLES_ENABLED && (
          <aside className="demo-toolbar" aria-label="Developer demo access controls">
            <div>
              <strong>Developer demo mode</strong>
              <span>Roles are simulated for testing only. This is not a real sign-in.</span>
            </div>
            <label htmlFor="demo-role">Simulated role</label>
            <select id="demo-role" value={group} disabled={loading || uploading} onChange={(event) => { setGroup(event.target.value); setResult(null); setError(""); setAnswerUnavailable(false); }}>
              <option value="">Public visitor</option>
              <option value="students">Student</option>
              <option value="staff">Staff member</option>
              <option value="admissions">Admissions team</option>
            </select>
          </aside>
        )}

        {uploadOpen && <DocumentUpload
          groups={group ? [group] : []}
          demoRolesEnabled={DEMO_ROLES_ENABLED}
          onBusyChange={setUploading}
          onUploaded={() => { setResult(null); setError(""); }}
        />}

        <section className="search-section" aria-labelledby="page-title">
          <p className="section-label">JKU STUDY INFORMATION</p>
          <h1 id="page-title">What would you like to know?</h1>
          <p className="intro">
            Ask about courses, prerequisites, exams, deadlines, or university regulations.
            Get an answer grounded in your documents, with clickable source tags.
          </p>

          {(!apiKey || editingKey) && (
            <section className="connection-card" aria-labelledby="connection-title">
              <div className="connection-copy">
                <span className="shield-icon" aria-hidden="true">✓</span>
                <div>
                  <p className="connection-step">ONE-TIME SETUP FOR THIS TAB</p>
                  <h2 id="connection-title">Connect an answer provider</h2>
                  <p>
                    JKUAI searches university documents locally. Your key is used only to turn
                    those sources into a clear answer.
                  </p>
                </div>
              </div>

              <form className="key-form" onSubmit={connectProvider}>
                <label htmlFor="answer-provider">Answer provider</label>
                <select id="answer-provider" disabled={loading} value={provider} onChange={(event) => {
                  setProvider(event.target.value as AnswerProvider);
                  setApiKey(""); setDraftApiKey(""); setShowApiKey(false);
                  setResult(null); setError(""); setAnswerUnavailable(false);
                }}>
                  <option value="gemini">Google Gemini — free tier available</option>
                  <option value="openai">OpenAI — separate API billing</option>
                </select>
                <label htmlFor="provider-key">{providerName} API key</label>
                <div className="key-input-row">
                  <input
                    id="provider-key"
                    type={showApiKey ? "text" : "password"}
                    value={draftApiKey}
                    onChange={(event) => setDraftApiKey(event.target.value)}
                    placeholder="Paste your key here"
                    autoComplete="off"
                    autoCapitalize="none"
                    spellCheck={false}
                  />
                  <button
                    className="show-key"
                    onClick={() => setShowApiKey((visible) => !visible)}
                    type="button"
                    aria-label={showApiKey ? "Hide API key" : "Show API key"}
                  >
                    {showApiKey ? "Hide" : "Show"}
                  </button>
                  <button className="connect-button" disabled={loading || !draftApiKey.trim()} type="submit">
                    Use this key
                  </button>
                  {editingKey && <button type="button" onClick={() => { setEditingKey(false); setDraftApiKey(""); setShowApiKey(false); }}>Cancel</button>}
                </div>
              </form>

              <div className="key-help">
                <p><strong>Private for this session.</strong> The key is not saved and is cleared when you refresh or disconnect.</p>
                {provider === "gemini"
                  ? <p><strong>Free tier has limits.</strong> Use a Google AI Studio project on the free tier. JKUAI cannot change your billing plan or guarantee free quota. Only the question and retrieved passages are sent to Google; review its data terms before using private documents.</p>
                  : <p><strong>Your account pays.</strong> OpenAI API usage is billed separately from ChatGPT.</p>}
              </div>

              <div className="key-links">
                <a href={provider === "gemini" ? "https://aistudio.google.com/apikey" : "https://platform.openai.com/api-keys"} target="_blank" rel="noreferrer">
                  Create a {providerName} API key <span aria-hidden="true">↗</span>
                </a>
                <details>
                  <summary>How is my key handled?</summary>
                  <p>
                    It stays in this browser tab and is sent through the JKUAI server to {providerName}
                    with each question. It is never added to browser storage, cookies, or the
                    JKUAI database. Use only a trusted JKUAI website with HTTPS.
                  </p>
                </details>
              </div>
            </section>
          )}

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
              <strong>{answerUnavailable ? "We couldn’t generate an answer." : "We couldn’t complete that search."}</strong>
              <p>{error}</p>
            </div>
            <button
              onClick={() => void runSearch(query)}
              type="button"
            >
              Try again
            </button>
          </section>
        )}

        {!loading && !error && !result && (
          <section className="how-it-works" aria-label="How search works">
            <div><span>1</span><p><strong>Ask naturally</strong>Use the same words you would use when asking a study advisor.</p></div>
            <div><span>2</span><p><strong>Review the results</strong>Read the answer and follow its source tags to the supporting passages.</p></div>
            <div><span>3</span><p><strong>Check the sources</strong>Read source passages and open linked documents to verify important details.</p></div>
          </section>
        )}

        {result && (
          <section className="results" aria-live="polite">
            <article className="answer-panel">
              <div className="panel-heading">
                <div>
                  <p className="section-label">{mode === "retrieval" || answerUnavailable ? "SOURCE RESULTS" : "ANSWER"}</p>
                  <h2>{sourceCount > 0 ? (mode === "retrieval" || answerUnavailable ? "Retrieved source passages" : "Based on retrieved documents") : "No matching source found"}</h2>
                </div>
                <span className="source-count">{sourceCount} {sourceCount === 1 ? "source" : "sources"}</span>
              </div>

              <div className="answer-text">
                <AnswerText answer={answerUnavailable ? "Answer generation failed. You can still inspect the retrieved passages below." : result.answer} sources={result.sources} />
              </div>

              {mode === "answer" && !answerUnavailable && sourceCount > 0 && result.exact_documents_used.length > 0 && (
                <div className="verification-note">
                  <span aria-hidden="true">✓</span>
                  <p><strong>Easy to verify</strong>Select a citation in the answer or open a source document to check the information.</p>
                </div>
              )}

              {result.exact_documents_used.length > 0 && (
                <details className="documents-used">
                  <summary>{mode === "retrieval" || answerUnavailable ? "Retrieved documents" : "Documents cited in this answer"} ({result.exact_documents_used.length})</summary>
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
                  <h2>Sources to inspect</h2>
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
                  {result.sources.map((source) => (
                    <article id={source.citation_id} key={source.chunk_id} className="source-card">
                      <div className="source-meta">
                        <a className="citation" href={`#${source.citation_id}`}>[{source.citation_id}]</a>
                        <span>{source.page_number ? `Page ${source.page_number}` : "Page not listed"}</span>
                      </div>
                      <h3>{source.title}</h3>
                      <p>{source.excerpt}</p>
                      {source.source_url && (
                        <a href={source.source_url} target="_blank" rel="noreferrer">
                          Open source document <span aria-hidden="true">↗</span>
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
        <p>JKUAI may make mistakes. Confirm important requirements against the original documents.</p>
      </footer>
    </div>
  );
}
