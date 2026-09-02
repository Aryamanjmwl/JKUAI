import argparse
import json
import statistics
import time

import httpx


def score_retrieval(
    retrieved_document_ids: list[str],
    relevant_document_ids: set[str],
    *,
    k: int = 5,
) -> tuple[float, float]:
    if not relevant_document_ids:
        raise ValueError("relevant_document_ids must contain at least one document")

    top_k = retrieved_document_ids[:k]
    recall = len(relevant_document_ids.intersection(top_k)) / len(relevant_document_ids)
    relevant_ranks = [
        rank
        for rank, document_id in enumerate(top_k, start=1)
        if document_id in relevant_document_ids
    ]
    reciprocal_rank = 1 / min(relevant_ranks) if relevant_ranks else 0.0
    return recall, reciprocal_rank


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
                f"{args.url}/search/retrieval",
                json={"query": row["question"]},
                headers={"X-User-Groups": ",".join(row.get("groups", []))},
            )
            response.raise_for_status()
            result = response.json()
            latencies.append((time.perf_counter() - started) * 1000)
            retrieved = [str(source["document_id"]) for source in result["sources"]]
            relevant = {str(document_id) for document_id in row["relevant_document_ids"]}
            recall, reciprocal_rank = score_retrieval(retrieved, relevant)
            recalls.append(recall)
            reciprocal_ranks.append(reciprocal_rank)
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
