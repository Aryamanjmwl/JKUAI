# JKUAI — Permission-Aware University Search

[![CI](https://github.com/Aryamanjmwl/JKUAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Aryamanjmwl/JKUAI/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-1d6747.svg)](LICENSE)

JKUAI searches university PDFs using BM25, vector embeddings, and cross-encoder
reranking. It can generate answers from retrieved passages with inline citations,
physical PDF page numbers, filenames, and source links when supplied.

Permission filters run before passages reach the reranker or answer generator.
PostgreSQL is the authority for access decisions, including when OpenSearch contains
an outdated grant. This is an independent portfolio prototype, not an official JKU service.

## Try it locally

The complete demo runs in Docker: PostgreSQL/pgvector, OpenSearch, FastAPI, and the React
client. You do not need host Python, Node.js, downloaded PDFs, or an OpenAI key for
source search.

**Requirements:** Git, Docker with Compose v2.20+, and a running Docker engine. On
Windows use Docker Desktop with Linux containers. Allow about 6 GB RAM and 10 GB free
disk space. The first build downloads Python packages and CPU inference dependencies;
the first seed downloads two ML models. Subsequent runs reuse image layers and a model
cache. The automated verification uses Linux x86-64 containers.

On Linux, OpenSearch requires `vm.max_map_count` of at least 262144. Check
`cat /proc/sys/vm/max_map_count`; if lower, run `sudo sysctl -w vm.max_map_count=262144`
before starting the services. Docker Desktop manages the Linux VM separately.

Clone the repository, then run these commands **from its root directory**. They work in
PowerShell and POSIX shells:

```sh
git clone https://github.com/Aryamanjmwl/JKUAI.git
cd JKUAI
docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d --build --wait --wait-timeout 180
docker compose -f docker-compose.yml -f docker-compose.demo.yml run --rm seed
```

The seed command must finish with `"status": "passed"`. It uploads three **clearly
labelled fictional university PDFs**, checks their ranking and role isolation, and
writes the PDFs and check report to `data/demo-output/`. These examples demonstrate the
pipeline; they are not actual university regulations. Repeating the seed is safe and
checks deduplication.

Open **<http://localhost:5173>**. Select **Search sources** and try:

| Role | Question | Expected result |
|---|---|---|
| Public visitor | What do I need before taking Advanced Machine Learning? | Course Guide ranks first; its excerpt names Introduction to Machine Learning and Linear Algebra. |
| Public visitor | What happens if I miss an exam because of illness? | Exam Regulations ranks first; the excerpt explains notification and a medical certificate. |
| Public visitor | What is the EXAM-OPS-42 internal routing code? | No Staff Operations passage or ORCHID-742 appears. Unrelated public passages can still appear. |
| Staff member | What is the EXAM-OPS-42 internal routing code? | Staff Operations ranks first and includes ORCHID-742. |

The Docker demo explicitly enables **simulated roles** in both services. They are not
login identities. Services bind to localhost; keep this configuration local.

### Add your own documents

Click **Add PDF** in the top-right corner, choose a text PDF, review its title, and click
**Upload PDF**. You can supply the original source URL so results link back to it.
The success message shows how many passages were indexed; the document is immediately
searchable. Uploading the same PDF again reuses its existing record.

In the local role demo, **Selected groups** lets you restrict retrieval to comma-separated
groups such as `students` or `staff`. Choose a matching simulated role to search a
restricted document. A duplicate with incompatible permissions returns a conflict;
reuploading is not an ACL-edit operation.

### Generate an answer

Switch to **Answer with citations**, enter a working OpenAI API key, and ask the course
prerequisite question. This is the only step requiring a paid provider account and
network access to OpenAI. The default model is `gpt-4.1-mini`; set `OPENAI_MODEL` in an
optional root `.env` and recreate the API to change it.

The key stays in browser-tab memory and is forwarded with answer requests. The backend
sends the question and accessible passages to OpenAI. Do not enter a key into an
untrusted hosted copy. Click an inline citation to inspect its passage. Missing or
unknown citation IDs trigger an insufficient-evidence response; valid IDs alone do
not prove factual support.

## Try a real university PDF

The fictional prerequisites above are not claimed to exist in this official curriculum.
For a real-document example, download the JKU Computer Science Master's curriculum
using [the native setup guide](docs/local-development.md#add-an-official-document),
then use the app’s upload form:

1. Download <https://studienhandbuch.jku.at/texte/1170_7_MS_ComputerScience.pdf>.
2. Click **Add PDF** at the top of the app. Select the PDF, enter a title and its source
   URL, and leave access set to **Everyone (public)**. Click **Upload PDF** and wait for
   **Document added**. Text PDFs up to 10 MiB are supported; scanned/encrypted PDFs are not.
3. Ask: **How many ECTS points is the written Master's thesis in Computer Science worth?**

The document smoke test checks a supporting passage on physical PDF page 7, along with
its filename, source URL, and citation ID. This is checked against the downloaded
curriculum version; inspect the PDF if the university replaces it. The original PDF
bytes are not retained by the API: keep your copy or provide a source URL.

## How it works

```mermaid
flowchart TD
    PDF["PDF pages"] --> Chunk["Text chunks and embeddings"]
    Chunk --> PG[("PostgreSQL / pgvector")]
    Chunk --> OS[("OpenSearch / BM25")]
    Q["Question and permitted groups"] --> Retrieve["Filtered vector and lexical retrieval"]
    PG --> Retrieve
    OS --> Retrieve
    Retrieve --> RRF["Reciprocal Rank Fusion"]
    RRF --> Rank["Cross-encoder reranking"]
    Rank --> Sources["Ranked passages with page metadata"]
    Sources --> Answer["Optional answer with citations"]
```

Each retriever supplies up to 20 candidates. RRF merges by chunk ID using
`1 / (60 + rank)` contributions. The best 20 fused candidates are reranked to at most
five passages. Lexical hits are reauthorized against PostgreSQL while their text is
loaded, blocking stale lexical grants. Scores are relevance rankings, not probabilities.

| Layer | Implementation |
|---|---|
| API | Python 3.11–3.13, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Storage | PostgreSQL 16 and 384-dimensional pgvector embeddings |
| Lexical search | OpenSearch 2.19 BM25 over titles and passage text |
| Local ML | `all-MiniLM-L6-v2` bi-encoder and `ms-marco-MiniLM-L-6-v2` cross-encoder |
| Generation | OpenAI Responses API; request-scoped key and bounded output |
| Client | React, TypeScript, Vite; Nginx serves the Docker build and proxies `/api` |
| Infrastructure | Docker Compose, persistent database/index/model volumes |

## API and verification

- Interactive API: <http://localhost:8000/docs>.
- `GET /health`: process liveness.
- `GET /ready`: migrated database and lexical index readiness; does not run model inference.
- `POST /search/retrieval`: sources without OpenAI usage.
- `POST /search`: generated answer, retrieved passages, cited filenames, and latency.

CI runs backend/API tests, client tests and build, real-store integration tests, and the
same Docker quickstart shown above. Chromium tests use the actual served UI and API to
check PDF upload, deduplication, source search, role isolation, answer-mode setup,
and a mobile viewport. Artifacts
include screenshots and service logs. Paid OpenAI answer quality is not tested in CI.

For native development, test commands, and document upload examples, see
[local development](docs/local-development.md). The retrieval evaluator reports
Recall@5, MRR@5, and latency from a supplied labelled question set; no representative
quality benchmark has been published.

## Stop or troubleshoot

```sh
docker compose -f docker-compose.yml -f docker-compose.demo.yml ps
docker compose -f docker-compose.yml -f docker-compose.demo.yml logs --tail 100 api opensearch
docker compose -f docker-compose.yml -f docker-compose.demo.yml stop
```

Stopping preserves documents and cached models. Do not add `-v` to `down` unless you
intend to delete the database, index, and model cache. Ports 5173, 8000, 5432, and 9200
must be free. If setup fails, inspect the service logs above; a seed error explains
whether the API is unreachable, not ready, or missing demo-role configuration.

## Scope and tradeoffs

- Default native API settings are public-only and ignore identity headers. The separate
  Docker demo enables role simulation. Verified authentication and administrative
  authorization for ingestion remain future work.
- Ingestion writes synchronously to two stores without a shared transaction. An outbox
  and retryable worker are needed for robust production indexing.
- Citation-ID validation checks syntax, not whether every claim follows from a passage.
  There is no calibrated relevance threshold or evaluated prompt-injection guarantee.
- HNSW exists in the migration; query plans and large-corpus recall/performance need measurement.

See [architecture](docs/architecture.md), [security](docs/security.md),
[verification evidence](docs/review.md), and the [demo walkthrough](docs/interview-demo.md).

## License

[MIT](LICENSE).
