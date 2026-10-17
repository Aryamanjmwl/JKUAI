# Native development

The root README's Docker demo is the shortest reviewer path. Use this guide to run or
change the API and client directly. Commands assume the repository root unless stated.
Use Python 3.11 or 3.12, Node.js 22.12+, and Docker Compose v2.20+.

## Windows / PowerShell 7

```powershell
git clone https://github.com/Aryamanjmwl/JKUAI.git
cd JKUAI
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[cpu,dev]"
Copy-Item .env.example .env
```

Copy the example only for a new checkout; preserve an existing `.env`. If PowerShell
blocks activation, use `.\.venv\Scripts\python.exe` explicitly instead. The remaining
commands assume activation succeeded.

```powershell
docker compose up -d --wait --wait-timeout 180
alembic upgrade head
$env:ENABLE_DEMO_ROLES="true"
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a **second terminal**, navigate to the cloned `JKUAI` root and activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/demo.py --check
```

In a **third terminal**, navigate to the cloned `JKUAI` root:

```powershell
cd frontend
npm ci
$env:VITE_ENABLE_DEMO_ROLES="true"
npm run dev
```

Open <http://localhost:5173>. Both native processes need the demo flag for role
simulation. Restart each process after changing its environment. A default API without
that flag intentionally ignores role headers.

## Linux / POSIX shell

```sh
git clone https://github.com/Aryamanjmwl/JKUAI.git
cd JKUAI
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[cpu,dev]'
cp .env.example .env
docker compose up -d --wait --wait-timeout 180
alembic upgrade head
ENABLE_DEMO_ROLES=true uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Set the Linux OpenSearch host requirement from the README before starting Compose.
In another terminal at the repository root:

```sh
. .venv/bin/activate
python scripts/demo.py --check
```

In another terminal at the repository root:

```sh
cd frontend
npm ci
VITE_ENABLE_DEMO_ROLES=true npm run dev
```

The API accepts browser origins at localhost or 127.0.0.1 on port 5173. Vite fails if
5173 is occupied, instead of silently changing to a port the API does not allow.
Stop the complete Docker demo before using native development on the same ports.

## Add an official document

In PowerShell, from the repository root with the API running:

```powershell
New-Item -ItemType Directory -Force -Path data\raw | Out-Null
Invoke-WebRequest -Uri "https://studienhandbuch.jku.at/texte/1170_7_MS_ComputerScience.pdf" -OutFile "data\raw\jku-ms-computer-science-curriculum.pdf"
curl.exe --fail-with-body -X POST http://localhost:8000/documents -F "file=@data/raw/jku-ms-computer-science-curriculum.pdf;type=application/pdf" -F "title=JKU Master's Curriculum in Computer Science" -F "source_url=https://studienhandbuch.jku.at/texte/1170_7_MS_ComputerScience.pdf" -F "visibility=public"
```

In a POSIX shell:

```sh
mkdir -p data/raw
curl --fail --location https://studienhandbuch.jku.at/texte/1170_7_MS_ComputerScience.pdf -o data/raw/jku-ms-computer-science-curriculum.pdf
curl --fail-with-body -X POST http://localhost:8000/documents -F 'file=@data/raw/jku-ms-computer-science-curriculum.pdf;type=application/pdf' -F "title=JKU Master's Curriculum in Computer Science" -F 'source_url=https://studienhandbuch.jku.at/texte/1170_7_MS_ComputerScience.pdf' -F 'visibility=public'
```

Expect a JSON response containing `document_id`, a positive `chunks_created` count,
and `duplicate: false` on the first upload. A repeat returns the same document ID and
`duplicate: true` when permissions match.

Ask a question the document supports, such as the written Master's thesis credit
allocation. The fictional Advanced Machine Learning prerequisites are demonstrated
by `demo-course-guide.pdf`, not by this real curriculum.

### Retrieval API example without an OpenAI key

PowerShell:

```powershell
$body = @{ query = "How many ECTS points is the written Master's thesis in Computer Science worth?" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/search/retrieval -Method Post -ContentType "application/json" -Body $body
```

POSIX shell:

```sh
curl --fail-with-body http://localhost:8000/search/retrieval -H 'Content-Type: application/json' -d '{"query":"How many ECTS points is the written Masters thesis in Computer Science worth?"}'
```

## Quality checks

With the Python environment active, from the root:

```sh
ruff check .
ruff format --check .
pytest -q
```

From `frontend`:

```sh
npm ci
npm test
npm run build
```

Backend unit/API tests do not need the ML extra, Docker, or provider credentials;
`pip install -e '.[dev]'` is sufficient for those checks. Running retrieval itself
requires `.[cpu]`.

With a live API in demo-role mode, opt into real-store tests:

```powershell
$env:RUN_INTEGRATION="1"
pytest -q tests/integration
```

Or, on Linux:

```sh
RUN_INTEGRATION=1 pytest -q tests/integration
```

The official-document test additionally needs `OFFICIAL_PDF` pointing to the downloaded
curriculum. The test changes and restores fixture ACLs; use a local test corpus.

With the full Docker demo running and seeded, run the actual browser checks from `frontend`:

```sh
npx playwright install chromium
npm run test:e2e
```

## Retrieval evaluation

Copy `evaluation/questions.example.jsonl` to a local ignored dataset and replace the
placeholder IDs with actual indexed document UUIDs and reviewed questions. Run:

```sh
python evaluation/evaluate.py evaluation/questions.jsonl
```

Group-specific rows require the API's demo-role setting. Metrics are document Recall@5
and MRR@5 over the first five returned chunks, plus mean and nearest-rank p95 latency.
This does not evaluate generated answer correctness or produce a representative
benchmark without a reviewed dataset.
