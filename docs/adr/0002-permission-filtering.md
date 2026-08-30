# ADR 0002: Filter permissions during retrieval

- Status: Accepted
- Date: 2026-08-30

## Context

Filtering restricted documents after retrieval can leak metadata and reduces the quality of the final candidate set.

## Decision

Store document visibility and group ACLs in both indexes. Filter candidates inside PostgreSQL and OpenSearch before ranking or generation. The API derives the caller's groups from an authentication boundary; development headers are only a local adapter.

## Consequences

The search service never receives unauthorized chunks. Before real deployment, replace trusted development headers with verified identity-provider claims and add ACL synchronization tests.
