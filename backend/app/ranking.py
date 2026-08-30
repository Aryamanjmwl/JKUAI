def reciprocal_rank_fusion(*rankings: list[dict], rank_constant: int = 60) -> list[dict]:
    """Merge ranked result lists without requiring comparable raw scores."""
    merged: dict[str, dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            chunk_id = str(hit["chunk_id"])
            current = merged.setdefault(chunk_id, dict(hit, fusion_score=0.0))
            current["fusion_score"] += 1.0 / (rank_constant + rank)
    return sorted(merged.values(), key=lambda item: item["fusion_score"], reverse=True)
