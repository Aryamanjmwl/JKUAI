import argparse
import json
import statistics
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    with open(args.dataset, encoding="utf-8") as dataset:
        rows = [json.loads(line) for line in dataset if line.strip()]
    recalls, reciprocal_ranks, latencies = [], [], []
    with httpx.Client(timeout=120) as client:
        for row in rows:
            started = time.perf_counter()
            response = client.post(
                f"{args.url}/search",
                json={"query": row["question"]},
                headers={"X-User-Groups": ",".join(row.get("groups", []))},
            )
            response.raise_for_status()
            result = response.json()
            latencies.append((time.perf_counter() - started) * 1000)
            retrieved = [str(source["document_id"]) for source in result["sources"]]
            relevant = set(row["relevant_document_ids"])
            recalls.append(float(bool(relevant.intersection(retrieved[:5]))))
            ranks = [i for i, doc_id in enumerate(retrieved, 1) if doc_id in relevant]
            reciprocal_ranks.append(1 / min(ranks) if ranks else 0.0)
    print(
        json.dumps(
            {
                "questions": len(rows),
                "recall_at_5": statistics.mean(recalls),
                "mrr": statistics.mean(reciprocal_ranks),
                "latency_ms_mean": statistics.mean(latencies),
                "latency_ms_p95": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)],
                "answer_correctness": "Add an LLM-judge or human score in phase 2",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
