# Interview demo

Use this guide to rehearse the local demo before the interview. Run the model downloads
and PDF ingestion beforehand; the first inference is slower than a warm request.

## Start the local demo

Follow the [README Docker quickstart](../README.md#try-it-locally). It runs the API,
client, indexes, and model inference without installing host Python or Node. Complete
the seed/check command before screen sharing and expect `"status": "passed"`.

For native development, use [local-development.md](local-development.md). All reviewer
setup commands target the default branch. The Docker demo explicitly enables simulated
roles; the native API is public-only unless configured otherwise.

The seed PDFs are fictional university examples and are visibly labelled. Open them
from `data/demo-output/` while explaining page citations. To show actual university
content, add the official curriculum using the README instructions and ask the written
Master’s thesis credit question. Do not attribute the fictional course prerequisites
to that curriculum.

Open <http://localhost:5173> and use **Ask JKUAI** first; without a key it shows retrieved passages.

## A five-minute walkthrough

| Time | Action | What to explain |
|---|---|---|
| 0:00–0:45 | Introduce the problem | University information is scattered across PDFs. Search needs exact identifiers, semantic matches, and traceable answers. |
| 0:45–1:45 | Choose Public visitor; ask “What do I need before taking Advanced Machine Learning?” | Read the course-guide excerpt and show its page and filename. Explain lexical retrieval plus embeddings, then fusion and reranking. |
| 1:45–2:45 | Ask “What is the EXAM-OPS-42 internal routing code?” as Public visitor, then Staff member | Public/student searches must not contain the staff operations document or ORCHID-742. Staff can retrieve it. Public search may still return unrelated public passages; do not describe that as a confidence score. |
| 2:45–3:45 | Connect a working OpenAI API key | Ask the course prerequisite question again. Click [S1] to inspect the supporting passage. Explain that retrieval is local; the permitted passages and question go to OpenAI for generation. |
| 3:45–4:30 | Open `services/search.py` and the live integration test | Point out the SQL and OpenSearch filters and the PostgreSQL recheck on lexical hits. The revocation test deliberately leaves the lexical ACL stale. |
| 4:30–5:00 | Discuss one limitation and next step | Real identity verification is the next security boundary. Outbox-backed ingestion is the next reliability improvement. |

If there is no working OpenAI key or quota, show source search and explain that answer
generation remains unverified in that session. Do not present a saved response as live
output. Keep keys out of screen sharing, terminal history, and screenshots.

## Explain the project in your own words

JKUAI searches university PDFs and uses the retrieved passages to answer questions with
citations. It combines BM25, which is useful for exact course names and identifiers,
with vector similarity, which helps when a question uses different wording. Reciprocal
Rank Fusion combines the two rankings, and a cross-encoder reranks the candidates.
Access filters run before the passages reach the generator. The current local demo
uses simulated groups; production authentication is still future work.

Be clear about the scope: this is an enterprise-search prototype, not a deployed university
service. Read the code paths below and rehearse explaining them without memorizing them.

## Questions to be ready for

**Why use both BM25 and vectors?** BM25 matches words and identifiers. Embeddings
represent meaning, so “graduate” can match text about “degree requirements.” Their
failure modes differ, which makes combining them useful. This still needs evaluation
on a representative corpus; it does not establish a measured improvement here.

**Why Reciprocal Rank Fusion?** BM25 scores and cosine similarity have different
scales. RRF uses rank positions: each appearance contributes `1 / (60 + rank)`. A chunk
found by both retrievers receives both contributions.

**What does the reranker add?** The bi-encoder embeds the question and each passage
separately. The cross-encoder reads each question/passage pair together, which allows
finer relevance scoring but costs more inference time. It is used on 20 fused candidates,
not on the entire corpus; five passages are returned.

**Where do permissions run?** In the SQL vector query and the OpenSearch lexical
query, before their top-k limits. Lexical IDs are then hydrated from PostgreSQL with
the SQL permission clause again. That last check blocks stale lexical permissions.

**Can a user just claim to be staff?** With the default settings, no: identity headers
are ignored and all searches are public-only. With explicit demo mode enabled, yes:
the role is simulated. That mode is only for a trusted local demonstration. A deployed
service needs verified tokens and server-derived groups.

**Why PostgreSQL and OpenSearch?** PostgreSQL stores the authoritative documents,
chunks, ACLs, and embeddings; pgvector provides cosine search. OpenSearch supplies
BM25. The tradeoff is operating and synchronizing two stores. A smaller system could
use PostgreSQL full-text search instead.

**Does it really use an approximate vector index?** The migration creates an HNSW
index using cosine distance. PostgreSQL chooses the query plan; for a tiny dataset it
may use an exact scan. Inspect `EXPLAIN ANALYZE` before claiming index usage or speed.

**What happens when a document is uploaded twice?** A unique SHA-256 checksum
identifies the stored PDF bytes. A compatible, authorized retry reuses the document
and republishes stored chunks to OpenSearch. Incompatible permissions or an inaccessible
duplicate produce a generic conflict rather than disclosing the document metadata.

**Are the two writes atomic?** No. PostgreSQL and OpenSearch do not share a
transaction. Search hydrates lexical IDs through PostgreSQL, so uncommitted/orphaned
lexical entries cannot supply source text. Retry helps with indexing recovery, but a
transactional outbox and background worker are the stronger long-term design.

**How is the PDF chunked?** Text is extracted page by page, whitespace is normalized,
and each page is split into roughly 900-character chunks with 150-character overlap.
The page boundary is preserved. These are character counts, not token counts.

**Why overlap?** It reduces information loss where an explanation crosses a chunk
boundary. It also produces redundant passages, so overlap and per-document diversity
should be evaluated rather than assumed optimal.

**What do citations guarantee?** They identify the source passages supplied to the
model. The API rejects a response with no citation or an unavailable source ID, except
for the explicit insufficient-evidence response. It does not prove that every sentence
is supported. Human evaluation or entailment checks are still needed.

**What if nothing supports an answer?** Empty retrieval returns an explicit no-source
message. For irrelevant but nonempty results, the generator is instructed to abstain.
There is no calibrated relevance threshold, and this abstention behavior has not yet
been benchmarked with a real LLM.

**Is the reranker score a confidence percentage?** No. It is a relevance score used
to order candidates, not a calibrated probability of answer correctness.

**How do you measure quality?** The evaluator reports Recall@5 and reciprocal rank
over the first five returned chunks' document IDs, plus latency. Duplicate chunks do not
inflate recall. A labelled representative question set, access cases, and human-reviewed
answer/citation correctness are still needed before publishing quality numbers.

**How does the system handle prompt injection?** Source text is treated as untrusted
in the system instructions, and unavailable citation IDs are rejected. These are limited
controls, not a demonstrated prompt-injection defense. ACL filtering is independent of
the LLM and occurs before source text is sent to it.

**What would you improve next?** Verified authentication and group mapping, an indexing
outbox, a representative evaluation set with retrieval ablations, and observability of
latency and failures. Start with these before adding more model complexity.

## Troubleshooting

| Symptom | Check |
|---|---|
| Docker services do not become healthy | `docker compose ps` and `docker compose logs`; ensure ports 5432/9200 are free and Docker Desktop has enough memory. On Linux, OpenSearch needs `vm.max_map_count` at least 262144. |
| Seed check fails for staff | Restart the API with `ENABLE_DEMO_ROLES=true`; setting only the frontend flag does not grant backend access. |
| Role selector is missing | Restart Vite with `VITE_ENABLE_DEMO_ROLES=true`. |
| First search takes a long time | Complete the model warmup, then run one search before screen sharing. |
| Search works but answers fail | Check the request key, provider billing/quota, network, and `OPENAI_MODEL` in `.env`. |
| Upload returns 409 | The same PDF already exists with an incompatible ACL, or the current role cannot access it. Use the correct role and original ACL. |
| No passages appear | Confirm the seed finished and `alembic upgrade head` succeeded. `/health` checks process liveness; `/ready` checks the migrated database and index. |

Stop the API and frontend with Ctrl+C. `docker compose stop` preserves the ingested
corpus. `docker compose down -v` deletes it; avoid that before the interview.
