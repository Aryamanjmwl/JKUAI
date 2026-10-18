# How JKUAI works

## Upload and storage

`POST /documents` accepts a text PDF with a title, optional HTTP(S) source URL, and
access settings. The default upload limit is 10 MiB. Scanned and encrypted PDFs are
not supported. The API keeps extracted text and metadata, not the original PDF bytes.

`services/pdf.py` uses pdfplumber to extract ruled tables with their column labels and
merged semester headings. Other pages use pypdf text extraction. Common WS/SS and
semester labels include English/German search aliases. Complex layouts can still need
manual inspection. `chunking.py` splits text blocks into roughly 900-character chunks
with 150-character overlap, preserving physical PDF page numbers.

The local `all-MiniLM-L6-v2` model produces normalized 384-dimensional vectors.
PostgreSQL stores documents, chunks, permissions, and embeddings. OpenSearch stores
chunk text and permission metadata for BM25 search.

A SHA-256 checksum identifies duplicate uploads. If the caller can access the document
and the supplied permissions match, a re-upload preserves its identity and metadata.
Changed extraction refreshes the passages and embeddings; unchanged extraction avoids
embedding work. The upload republishes current lexical entries and removes obsolete
ones. Incompatible or inaccessible duplicates return a generic conflict.

The two stores do not share a transaction. New uploads write the lexical index before
committing PostgreSQL. Refreshes commit updated SQL rows before repairing the lexical
index. SQL hydration rejects orphaned or revoked lexical entries. An outbox and retryable
worker remain the stronger production design; concurrent duplicate uploads can still
hit the unique-checksum constraint.

## Search

1. The default API treats callers as anonymous. Explicit demo mode accepts simulated
   user/group headers; these are not verified identities.
2. `services/query.py` adds deterministic English/German semester search aliases.
   Keyword search also adds German equivalents of common English university terms
   (for example, grade/Beurteilung and exam/Prüfung). These extra terms do not enter
   embedding or reranking queries. This limited glossary is not general translation;
   the original question is retained for generation. No reindexing or provider call is needed.
3. PostgreSQL filters document permissions before retrieving up to 20 chunks by cosine
   distance. OpenSearch independently filters permissions before returning up to 20
   BM25 matches over `title^2` and `content`. When keyword aliases are added, a second
   keyword request runs concurrently; its matches supplement the original 20.
4. Lexical IDs are loaded from PostgreSQL with its permission filter again. This blocks
   stale lexical grants. Stale denials may still reduce recall until indexing is repaired.
5. Reciprocal Rank Fusion merges both lists by chunk ID, adding `1 / (60 + rank)` for
   each occurrence. The union, at most 60 candidates with expansion or 40 without it
   by default, reaches the reranker. Original-channel hits are preserved until this step.
6. The local multilingual `mmarco-mMiniLMv2-L12-H384-v1` cross-encoder returns the best
   five passages. Scores are relevance rankings, not confidence percentages.

`POST /search/retrieval` returns these passages with IDs, filenames, page numbers,
optional source URLs, scores, and latency. It makes no provider request. The migration
creates a cosine HNSW index, but the database chooses the query plan. Large-corpus
performance and approximate-vector recall under permissions need measurement.

## Answers and the client

`POST /search` follows the same retrieval path, then calls the chosen provider with the
original question and accessible passages. The API defaults to `openai`; the UI defaults
to `gemini`. Only the matching request header is used:

| Provider | Header | Default model | API |
|---|---|---|---|
| Gemini | `X-Gemini-API-Key` | `gemini-3.1-flash-lite` | Google OpenAI-compatible Chat Completions |
| OpenAI | `X-OpenAI-API-Key` | `gpt-4.1-mini` | OpenAI Responses |

Provider calls use a 30-second timeout and at most one retry. Output is bounded to
2,048 tokens for Gemini and 700 for OpenAI; OpenAI requests set `store=False`.
Gemini output must finish normally. Empty output, missing citations, or unknown citation
IDs produces an insufficient-evidence response. This validates IDs, not factual support.
The prompt asks for supported partial answers, official course names, and clear limits.

The response includes every retrieved passage. `exact_documents_used` lists filenames
actually cited in an answer, or retrieved filenames for a retrieval-only response.
The React client renders Markdown and clickable source tags without executing raw HTML
or loading model-supplied images. Generation failures preserve source-search access.
Keys remain in tab memory and are cleared on refresh, Disconnect, or provider changes.

## Running and checking it

The base Compose file runs PostgreSQL and OpenSearch for native development. The demo
overlay adds FastAPI, the React/Nginx client, a model cache, and a seed tool. Services
bind to localhost. Nginx proxies `/api` to FastAPI; the API applies migrations at startup.

`GET /health` checks process liveness. `GET /ready` checks a migrated database table and
the lexical index; it does not load models. The seed/check command exercises inference.
CI also checks real PDFs, duplicate refresh, access revocation, uploads, and browser flows.
The evaluator in `evaluation/` measures retrieval, not generated answer correctness.

See [local development](local-development.md), [security](security.md), and the
[demo walkthrough](interview-demo.md). Design decisions are recorded in [the ADRs](adr/).
