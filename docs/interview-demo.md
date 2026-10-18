# Short interview walkthrough

## Prepare

Follow the [README setup](../README.md#run-locally) and run the seed/check command.
Download models, upload any real PDFs, and test a question before screen sharing.
The first search is slower. Keep API keys off screen.

Demo PDFs are explicitly fictional. For real university information, upload the
curriculum linked in the README and ask a question that its version supports.
A recommended study plan is not a live registration timetable.

## Five-minute demo

| Step | Show | Explain |
|---|---|---|
| 1 | Ask the Advanced Machine Learning example without a key | Local retrieval finds the fictional course guide; inspect its passage and page. |
| 2 | Search for the EXAM-OPS-42 routing code as Public visitor, then Staff member | The restricted staff passage appears only for the matching simulated role. Roles are a demo, not authentication. |
| 3 | Connect Gemini or OpenAI and repeat a supported question | Generation uses accessible passages; click a citation to inspect the evidence. Without quota, show retrieval honestly. |
| 4 | Upload a real curriculum and ask about its recommended winter-semester courses | Show the PDF version and page; distinguish study recommendations from personal eligibility. |
| 5 | Describe one limitation | Real login, authorized uploads, reliable indexing, and broader quality evaluation remain production work. |

## Explain the implementation simply

**Why two search methods?** BM25 matches words and identifiers. Embeddings can match
similar meaning. Their rankings are combined, then a cross-encoder reads each
question/passage pair to select the best five sources. A representative benchmark is
still needed to measure the benefit over either search method alone.

**How are rankings combined?** Each retriever returns up to 20 permitted chunks.
Reciprocal Rank Fusion adds `1 / (60 + rank)` for each occurrence. The complete union,
at most 40 candidates by default, reaches the reranker. It includes candidates found
by only one retriever. The reranker is multilingual; semester query aliases also help
English/German matching. This is not general automatic translation.

**Where are permissions checked?** In PostgreSQL and OpenSearch before their result
limits. Lexical IDs are checked against PostgreSQL again before text reaches ranking.
The integration test deliberately leaves an outdated lexical grant to test revocation.
Default settings ignore identity headers; demo mode trusts them for local simulation.

**What happens on a duplicate upload?** Matching bytes and compatible permissions
reuse the document. Changed extraction refreshes its passages and embeddings. The
original metadata and permissions remain unchanged. The two stores are not updated
atomically; a transactional outbox would improve reliability.

**How are PDFs handled?** Ruled tables retain column relationships and semester
headers. Text blocks are split into about 900 characters with 150-character overlap,
while keeping physical page numbers. Scans require OCR before upload.

**What do citations prove?** They locate the passages supplied to the model. Missing
or unknown source IDs are rejected. A valid ID does not prove that a claim follows
from the passage. The model is asked to state when evidence is missing.

**What is tested?** Backend validation, permissions, provider contracts, frontend
behavior, real-store retrieval, PDF refresh, and browser flows. CI provider responses
are simulated. Live answers require a working key and must be checked separately.
The retrieval evaluator reports Recall@5, MRR@5, and latency on a labelled dataset;
there is no published representative accuracy benchmark.

Useful files: `backend/app/services/search.py`, `backend/app/services/ingestion.py`,
`backend/app/services/generation.py`, and `tests/integration/test_live_pipeline.py`.
See [architecture](architecture.md) and [security](security.md) for details.
