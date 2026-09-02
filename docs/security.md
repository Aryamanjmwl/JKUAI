# Security and trust boundaries

JKUAI is a local development and portfolio system. Its default configuration is not a
production deployment profile. This document describes the controls that exist today,
the boundaries they rely on, and the work required before exposing the service to users.

## Current trust model

The default application treats every caller as anonymous. It searches only documents
whose visibility is `public`; caller-supplied user and group headers are ignored.
Permission filters are applied independently in PostgreSQL and OpenSearch before result
fusion, reranking, and answer generation.

Setting `ENABLE_DEMO_ROLES=true` changes this boundary. The API then accepts
`X-User-Id` and `X-User-Groups` as simulated identity data so permission behaviour can
be demonstrated locally. These headers are not proof of identity. Developer demo mode
must remain disabled anywhere that is reachable by untrusted users.

## Security posture by surface

| Surface | Current control | Remaining risk |
|---|---|---|
| Search | Anonymous callers are restricted to public documents | No user authentication, abuse controls, or request quotas |
| Restricted documents | ACL filtering occurs in both retrieval engines | Group membership is simulated in developer mode; no identity provider or ACL synchronization |
| Document ingestion | File type and visibility values are validated | `POST /documents` is unauthenticated and intended only for local use |
| OpenAI credential | Accepted per request and not intentionally persisted by the application | A browser-supplied key passes through the API process and any surrounding infrastructure |
| Generated answers | The model is instructed to use retrieved sources and emit source markers | Prompt injection and citation correctness are not yet automatically evaluated |
| Local infrastructure | Docker services are convenient and reproducible | Default database credentials and disabled OpenSearch security are unsuitable for deployment |
| Data at rest | Documents and chunks remain in local Docker volumes | Encryption, backup policy, retention, and secure deletion are not configured |

## OpenAI key handling

The web client keeps the key in React component state for the current page. It does not
write the key to local storage, session storage, cookies, PostgreSQL, or OpenSearch. The
backend constructs a request-scoped OpenAI client and does not deliberately log or save
the header.

This reduces accidental persistence; it does not make entering a key into an arbitrary
website safe. Browser extensions, a compromised frontend, reverse-proxy logs, tracing
systems, or a compromised server could still expose it. The bring-your-own-key flow is
therefore limited to a trusted local demonstration. It should not be offered by a public
deployment.

A production service should keep the provider credential in server-side secret storage,
never send it to the browser, and protect its use with authenticated accounts, rate
limits, per-user quotas, spending alerts, and credential rotation.

## Local-development assumptions

The supplied Compose file exposes PostgreSQL and OpenSearch to the host, uses a known
development database password, and disables OpenSearch security. Run it only on a
trusted development machine and do not deploy the Compose configuration to a public
host. Keep `.env`, downloaded documents, model artifacts, and local database volumes
out of Git.

## Production requirements

Before deployment to untrusted users:

1. Add an identity provider and validate signed sessions or tokens at the API boundary.
2. Derive groups server-side and test ACL synchronization, revocation, and index parity.
3. Restrict document ingestion to an authenticated administrative role.
4. Store OpenAI credentials in a managed secret store and remove browser key entry.
5. Put the API behind HTTPS, a restrictive proxy, rate limits, request-size limits, and
   explicit security headers.
6. Replace development database credentials; enable transport authentication and
   encryption for both data stores; restrict their network exposure.
7. Redact sensitive headers in application, proxy, tracing, and error-reporting systems.
8. Add dependency scanning, container scanning, audit events, backup and retention
   policies, and an incident-response process.
9. Test prompt-injection resistance, citation validity, document isolation, and direct
   object-reference attacks.

## Reporting a vulnerability

Do not include credentials, private documents, or personal data in a public issue.
Until a private reporting channel is configured, report only non-sensitive reproduction
details through the repository issue tracker.
