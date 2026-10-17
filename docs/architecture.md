# Pipeline and implementation map

## Ingestion

`POST /documents` validates the title, HTTP(S) source URL, visibility, required groups,
and upload size. The default limit is 10 MiB. Filenames are reduced to their basename.
Encrypted, corrupt, and image-only PDFs are rejected; there is no OCR pipeline.

`services/ingestion.py` hashes the PDF bytes, extracts text with pypdf, and calls
`chunk_pages`. Each chunk retains its physical PDF page number; this may differ from a
page number printed inside the document. Empty pages are skipped. The original PDF
bytes are not retained by the API; the database stores text, metadata, and embeddings.
Keep uploaded PDFs yourself or provide an authoritative source URL.

The sentence-transformer produces normalized 384-dimensional embeddings. SQLAlchemy
writes `Document` and `Chunk` rows. OpenSearch receives each chunk's ID, document ID,
title, text, visibility, and groups, using the chunk UUID as the index ID. Bulk writes
use `refresh=wait_for`, so successful uploads are immediately searchable lexically.

The writes are synchronous and span two systems. PostgreSQL is committed after the
lexical write. If a later commit fails, lexical entries may remain orphaned; retrieval
ignores entries that cannot be hydrated from PostgreSQL. A compatible duplicate retry
reindexes stored chunks. This does not replace an outbox or provide full crash recovery.
Concurrent identical uploads may still encounter the unique-checksum constraint.

## Retrieval

1. `security.get_user_context` returns an anonymous principal by default. With explicit
   local demo mode it accepts simulated identity/group headers.
2. `services/search.hybrid_search` embeds the query with the same bi-encoder used for
   ingestion. SQL joins chunks to documents, filters permissions, orders by cosine
   distance, and limits results to `RETRIEVE_K` (20 by default).
3. OpenSearch runs `multi_match` over `title^2` and `content`, using BM25. Its Boolean
   filter permits public documents or matching groups, before its own top-20 limit.
4. Lexical chunk IDs are hydrated from PostgreSQL under the authoritative ACL filter.
   This protects against stale grants in OpenSearch. A stale denial can still reduce
   recall until the lexical ACL is synchronized; revocation safety is not index parity.
5. `ranking.reciprocal_rank_fusion` merges by chunk UUID. Each retriever contributes
   `1 / (60 + rank)`. The best 20 fused candidates proceed to the reranker.
6. A local cross-encoder scores query/passage pairs. The best `RERANK_K` (five) passages
   are returned. Cross-encoder and fusion scores are not probabilities.

`POST /search/retrieval` stops here. It returns excerpts, page numbers, document/chunk
UUIDs, filenames, optional source URLs, scores, and latency, without an OpenAI request.

The pgvector migration includes a cosine HNSW index. The database planner chooses
whether to use it; this repository has no measured large-corpus scaling result. ACL
filters and approximate nearest-neighbor scans require recall testing at realistic
cardinality before tuning HNSW search parameters.

## Generation and attribution

`POST /search` uses the same retrieval path. The request-scoped OpenAI client receives
the question and the permitted passages with stable `[S1]`…`[Sn]` IDs. It uses the
configured Responses API model (default `gpt-4.1-mini`) with a 30-second request
timeout, one retry, and a 700-token output limit. Requests use `store=False`; this
does not replace a review of the provider’s data-retention policies.
`X-OpenAI-API-Key` is supplied by the trusted local client and is not persisted by the
application. The question and retrieved text are sent to the provider.

The prompt asks for source-supported claims and abstention when evidence is insufficient.
A syntax guard rejects empty outputs, missing citation IDs, and invented IDs by returning
a fixed insufficient-evidence message. It cannot verify entailment, factual correctness,
or resistance to prompt injection.

`sources` contains all passages supplied to the model. In a generated answer,
`exact_documents_used` lists the unique filenames referenced by recognized citation IDs;
in a retrieval-only response it lists the unique retrieved filenames. Source excerpts contain the complete retrieved chunk, so a reviewer can inspect the
same passage that the model received even when no external source URL was provided.

## Trust boundary

The current ingestion endpoint is a local administrative tool without authentication.
The role selector is a demonstration aid. Do not describe this project as authenticated,
SSO-integrated, multi-tenant, or ready for public deployment. The default profile ignores
identity headers, and the Compose database/search ports bind to localhost.

The evaluator reports document Recall@5 and `mrr_at_5` over the first five returned
chunks, with nearest-rank p95 latency. It does not deduplicate the ranking into five
distinct documents before applying the cutoff.

See [security.md](security.md) for deployment requirements and
[interview-demo.md](interview-demo.md) for reproducible examples.


## Local deployment

The base Compose file starts the two stores for native development. The explicit
`docker-compose.demo.yml` overlay adds the API and Nginx-served React build, a persistent
model cache, and a seed tool. The API container applies migrations before startup.
Nginx proxies `/api` to the API over the Compose network, so the browser uses one origin.
Both demo-role settings are enabled by this overlay; it is not a production profile.
`/ready` queries a migrated table and checks that the lexical index exists; model
inference is verified by the seed command rather than the liveness endpoint.
