# JKUAI

[![CI](https://github.com/Aryamanjmwl/JKUAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Aryamanjmwl/JKUAI/actions/workflows/ci.yml)

JKUAI helps you search university PDFs and ask questions about them. Answers include
clickable source tags, document names, and PDF page numbers so you can check the evidence.
This is an independent portfolio project, not an official JKU service.

- Upload your own text PDFs, including course and semester tables.
- Search locally without an API key.
- Connect Gemini or OpenAI for answers based on the retrieved passages.
- Demonstrate access filtering with simulated student and staff roles.

## Run locally

Install **Git** and **Docker Desktop** with Linux containers, then start Docker.
Allow around 6 GB of memory and at least 10 GB of free disk space. The first run
can take several minutes to download dependencies and local search models.
Host Python and Node.js are not needed for the Docker setup.

On native Linux, OpenSearch also needs `vm.max_map_count` of at least 262144:
run `sudo sysctl -w vm.max_map_count=262144` if it is lower.

From PowerShell or a terminal:

```sh
git clone https://github.com/Aryamanjmwl/JKUAI.git
cd JKUAI
docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d --build --wait --wait-timeout 180
```

Open **<http://localhost:5173>**.

To load the optional fictional demo PDFs and check the search pipeline, run:

```sh
docker compose -f docker-compose.yml -f docker-compose.demo.yml run --rm seed
```

Expect `"status": "passed"`. The demo documents are test examples, not university rules.
Try **What do I need before taking Advanced Machine Learning?** or switch between
Public visitor and Staff member for **What is the EXAM-OPS-42 internal routing code?**
The staff document should appear only for the matching simulated role.

## Use your own PDF

1. Click **Add PDF**, choose a file, review the title, and click **Upload PDF**.
2. Add the original document URL if you want a link back to the PDF.
3. Ask a question supported by that document and inspect the source tags.

Text PDFs up to 10 MiB are supported. Scanned PDFs need OCR first; encrypted PDFs are
not supported. Re-uploading the same file preserves its identity and permissions and
refreshes its passages if extraction has changed. Keep your PDF copy: the app stores
extracted text, not the original file.

For a real example, download the [Bachelor Informatik curriculum](https://studienhandbuch.jku.at/texte/1171_12_BS_Informatik.pdf),
upload it, and ask **Which courses are recommended for the first winter semester?**
A recommended study plan does not establish current registration availability or
personal eligibility. Always inspect the cited document and its version.

## Connect an answer provider

Select **Google Gemini** or **OpenAI**, enter that provider's API key, and click
**Use this key**. Gemini is selected by default. Get a key from
[Google AI Studio](https://aistudio.google.com/apikey) or the
[OpenAI platform](https://platform.openai.com/api-keys).
Your provider project needs API access and available quota; check its current pricing
and limits. The app does not supply credits or automatically switch providers.

Use **Change API key** to replace a key. Keys stay in this tab's memory and are cleared
on refresh, Disconnect, or a provider switch. The question and retrieved passages go to
the selected provider, so review its data terms before using private documents.
Without a key, or if generation fails, you can still inspect source passages.

## Update, stop, or troubleshoot

From the repository folder, update and rebuild:

```sh
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d --build --wait --wait-timeout 180
```

Refresh the browser after updating. To inspect problems or stop the app:

```sh
docker compose -f docker-compose.yml -f docker-compose.demo.yml ps
docker compose -f docker-compose.yml -f docker-compose.demo.yml logs --tail 100 api opensearch
docker compose -f docker-compose.yml -f docker-compose.demo.yml stop
```

Stopping preserves documents and cached models. `down -v` deletes the project's data
volumes. If Docker cannot start, check that its engine is running and its data disk has
free space. Ports 5173, 8000, 5432, and 9200 must be available.

## Development and limits

The stack is React/TypeScript, FastAPI, PostgreSQL/pgvector, OpenSearch, and local
embedding/reranking models. Gemini or OpenAI provides optional answer generation.
CI checks the backend on Windows and Linux, the frontend build, real search services,
and Chromium browser flows. Provider responses are simulated in CI; live answer quality
and corpus-wide retrieval accuracy are not established by those tests.

**Keep the demo local.** Roles are simulated, uploads are unauthenticated, and the
Docker settings are for development. Public deployment needs real authentication,
server-verified permissions, and production infrastructure. Source tags provide
traceability, not a guarantee that every generated claim is correct.

English and German questions are accepted. German keyword aliases help English questions
find German passages, but bilingual accuracy is still being evaluated. In a small manual
check before this change, two English questions missed answers that their German versions
found. This is a known retrieval limitation, not an API-key problem. Check document dates:
an older university guide does not establish today's rules or contact details.

- [Local development and tests](docs/local-development.md)
- [How the search pipeline works](docs/architecture.md)
- [Security boundaries](docs/security.md)
- [Short interview walkthrough](docs/interview-demo.md)
- [Contributing](CONTRIBUTING.md)

[MIT license](LICENSE).
