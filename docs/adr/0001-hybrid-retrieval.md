# ADR 0001: Separate lexical and vector indexes

- Status: Accepted
- Date: 2026-08-30

## Context

University questions contain both exact identifiers such as course codes and semantic requests phrased differently from the source documents. Neither lexical nor vector retrieval handles both cases reliably by itself.

## Decision

Use OpenSearch BM25 for lexical retrieval and PostgreSQL with pgvector for semantic retrieval. Apply the same access-control predicate to each system before merging results with Reciprocal Rank Fusion. Rerank the merged top 20 with a cross-encoder and expose the best five chunks to answer generation.

## Consequences

This design makes each retrieval stage measurable and replaceable, but introduces dual-write consistency concerns during ingestion. A production deployment should move indexing to an outbox-backed worker. The initial version performs a synchronous dual write and reports failures rather than hiding them.
