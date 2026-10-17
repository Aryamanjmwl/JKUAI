# ADR 0002: Filter permissions during retrieval

- Status: Accepted
- Date: 2026-08-30

## Context

Filtering restricted documents after retrieval can leak metadata and reduces the quality of the final candidate set.

## Decision

Store document visibility and group ACLs in both indexes. Filter candidates inside
PostgreSQL and OpenSearch before ranking or generation. Recheck lexical chunk IDs
against PostgreSQL permissions during hydration; index ACLs can be stale. PostgreSQL
is the authority for whether source text can reach reranking and generation.

The default API treats callers as anonymous and ignores caller-supplied identity
headers. Only public documents are searchable. An explicit developer setting can enable
headers that simulate group membership for local demonstrations; this mode is not an
authentication boundary.

## Consequences

Restricted chunks are removed before fusion, reranking, and generation. This protects
the default public-only path while preserving relevant candidates for authenticated
users in a future deployment.

Before deployment, replace simulated headers with verified identity-provider claims,
derive groups server-side, and implement ACL synchronization. The live integration
test covers revocation safety when OpenSearch still has the old group grant. The local
security assumptions and production requirements are documented in
[`docs/security.md`](../security.md).
