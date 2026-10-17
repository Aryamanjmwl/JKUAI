# Review and verification

Reviewed against the CV description: permission-aware hybrid search and RAG using
Python, FastAPI, PostgreSQL/pgvector, OpenSearch, React, and Docker.

## Claim-to-code map

| CV claim | Implementation and evidence | Qualification |
|---|---|---|
| Python / FastAPI | Typed request/response models and `/documents`, `/search/retrieval`, `/search` routes in `backend/app/main.py` | Local development service; ingestion has no administrative authentication. |
| PostgreSQL / pgvector | `models.py`, Alembic migration, cosine-distance query in `services/search.py` | HNSW is created; actual plan selection and scale have not been benchmarked. |
| OpenSearch / BM25 | Text mappings and `multi_match` over boosted titles and chunk text | Two stores require synchronization and operational work. |
| Hybrid search | `ranking.reciprocal_rank_fusion` merges lexical and vector rankings | A representative ablation study has not established an improvement over either retriever alone. |
| Embeddings / reranking | MiniLM sentence-transformer embeddings and MiniLM cross-encoder in `services/ml.py` | Local CPU inference; first use loads model weights. |
| Grounded answers with citations | Retrieved passages sent through Responses API, source IDs, page metadata, excerpts, cited filenames | Syntax checks validate IDs, not factual entailment. Live provider answer quality was not evaluated during this review. |
| Permission-aware retrieval | Both retrievers filter ACLs; lexical text is reauthorized in PostgreSQL | Default is public-only. Local role simulation is not authentication or SSO. |
| React | TypeScript client with source search, answer mode, role demo, errors, and source cards | API keys remain in tab memory; use the key flow only on a trusted local instance. |
| Docker | Compose runs PostgreSQL/pgvector and OpenSearch with health checks and persistent volumes | API and frontend run as host processes; this is not an all-services container deployment. |

The CV description is supportable as a description of a portfolio prototype. In an
interview, qualify permission-aware retrieval as demonstrated ACL filtering with
simulated groups, and describe citations as traceability rather than guaranteed truth.

## Findings addressed

| Finding | Change | Regression coverage |
|---|---|---|
| Lexical hydration trusted potentially stale OpenSearch ACLs | Reapply authoritative SQL permissions before source text reaches ranking | SQL query regression and live PostgreSQL revocation while the lexical grant remains stale |
| Duplicate upload could disclose restricted metadata or reuse incompatible permissions | Generic conflict for inaccessible/incompatible duplicates; authorized retries reindex stored metadata | Ingestion tests and live duplicate/conflict checks |
| Every retrieved filename was labelled as used by the answer | Derive cited filenames from recognized answer markers | API test with a retrieved but uncited document |
| Missing or invented citation IDs passed through | Explicit insufficient-evidence fallback | Invalid-ID cases and real SDK request/response parsing against a mock HTTP provider |
| UI could not demonstrate retrieval without an OpenAI account | Separate source search and answer modes | Client request tests and rendered React interaction tests |
| Corrupt/oversized PDFs and invalid metadata could fail unpredictably | Bounded reads; PDF, title, HTTP(S) URL, and query validation | API validation tests and fixture PDF round-trip tests |
| Default model setting was ambiguous | Explicit documented `gpt-4.1-mini` ID; request timeout, output bound, and `store=False` | Real SDK contract test without an external provider call |
| p95 used a lower rank for small datasets | Nearest-rank percentile; explicit `mrr_at_5` output label; reject empty datasets | Two-observation and 20-observation percentile tests |
| No repeatable live pipeline check | Deterministic fictional PDFs, seed/check command, full-stack CI | Actual pgvector, BM25, model inference, deduplication, role isolation, and stale-grant test |
| University-document example had not been exercised by tests | Download and retrieve from the official JKU Computer Science curriculum in CI | Check supporting thesis-credit passage, physical page 7, document identity, and source URL |

The explicit model identifier is listed in the
[OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
A working key with access and quota is still necessary to verify answer generation live.

## Verification record

Local checks on 17 October 2026:

- `ruff check .`: passed.
- `ruff format --check .`: passed.
- `pytest -q`: 47 passed; two live-stack tests skipped by default.
- `npm test`: 10 passed, including rendered client interaction tests.
- `npm run build`: passed.
- Synthetic PDF generation is deterministic and round-trips through the actual parser.

The full-stack GitHub Actions job starts the checked-in Compose services, applies the
actual migration, downloads and warms the real embedding/reranker models, starts the
API, and runs the seed/check command plus opt-in tests. The downloadable
`integration-evidence` artifact contains the synthetic check report and service logs.
The [pull request checks](https://github.com/Aryamanjmwl/JKUAI/pull/2/checks) identify
the exact tested commit. The initial full-stack run passed all synthetic retrieval,
duplicate, role-isolation, and stale-grant revocation checks:
[run 39024726686](https://github.com/Aryamanjmwl/JKUAI/actions/runs/39024726686).
The additional official-document check is covered by the subsequent run on the final
branch revision; inspect its status before the interview.

These checks establish working mechanics and regression protection. They do not
establish retrieval accuracy across a university corpus, production security, or
LLM factual/citation accuracy. No paid provider call was made during this review.

## Remaining work

1. Replace simulated roles with verified identity-provider claims and authorize ingestion.
2. Introduce a transactional outbox and retryable indexing worker; handle concurrent
   identical uploads gracefully rather than relying only on a unique constraint.
3. Build a reviewed question set and measure lexical/vector/hybrid/reranked variants.
   Evaluate answer correctness and citation support separately from retrieval metrics.
4. Add observability, rate limits, dependency/container scanning, and deployment secrets.
5. Evaluate approximate-vector recall under ACL filters and realistic corpus sizes.
6. Add OCR if scanned PDFs become part of the target corpus.

See [the demo guide](interview-demo.md) for the rehearsal steps and interview questions,
and [the implementation map](architecture.md) for a more detailed code walkthrough.
