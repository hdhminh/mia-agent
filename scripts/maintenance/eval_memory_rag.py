from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "tests/fixtures/memory_rag_golden.json"


STOPWORDS = {
    "anh",
    "ban",
    "bạn",
    "bi",
    "bị",
    "cho",
    "co",
    "có",
    "cua",
    "của",
    "dung",
    "dùng",
    "duoc",
    "được",
    "hay",
    "hoi",
    "hỏi",
    "khong",
    "không",
    "la",
    "là",
    "mia",
    "minh",
    "mình",
    "nen",
    "nên",
    "neu",
    "nếu",
    "the",
    "thế",
    "thi",
    "thì",
    "vao",
    "vào",
    "ve",
    "về",
    "to",
    "the",
    "and",
    "or",
}


def _tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[\wÀ-ỹ]+", str(value or "").lower())
        if len(token) > 1 and token not in STOPWORDS
    }
    expanded = set(tokens)
    for token in tokens:
        if token == "postgresql":
            expanded.add("postgres")
        if token == "github":
            expanded.add("git")
        if len(token) > 6:
            expanded.add(token[:6])
    return expanded


def _rrf(rank: int, *, k: int = 60) -> float:
    return 1.0 / (k + max(1, rank))


@dataclass(frozen=True)
class Candidate:
    id: str
    text: str
    kind: str = "semantic"
    importance: int = 3


def _rank_candidates(query: str, candidates: Iterable[Candidate]) -> list[str]:
    query_tokens = _tokens(query)
    semantic_ranked: list[tuple[float, Candidate]] = []
    lexical_ranked: list[tuple[float, Candidate]] = []
    for candidate in candidates:
        candidate_tokens = _tokens(candidate.text)
        if not candidate_tokens:
            continue
        overlap = len(query_tokens & candidate_tokens)
        semantic_score = overlap / math.sqrt(max(1, len(query_tokens)) * len(candidate_tokens))
        lexical_score = overlap + (2 if query.lower() in candidate.text.lower() else 0)
        semantic_ranked.append((semantic_score, candidate))
        lexical_ranked.append((lexical_score, candidate))

    semantic_order = {
        candidate.id: index
        for index, (_score, candidate) in enumerate(
            sorted(semantic_ranked, key=lambda item: (-item[0], item[1].id)),
            start=1,
        )
    }
    lexical_order = {
        candidate.id: index
        for index, (_score, candidate) in enumerate(
            sorted(lexical_ranked, key=lambda item: (-item[0], item[1].id)),
            start=1,
        )
    }
    by_id = {candidate.id: candidate for _score, candidate in semantic_ranked}
    scored = []
    for candidate_id, candidate in by_id.items():
        score = _rrf(semantic_order[candidate_id]) + _rrf(lexical_order[candidate_id])
        score += min(max(candidate.importance, 1), 5) * 0.00005
        scored.append((score, candidate.id))
    return [candidate_id for _score, candidate_id in sorted(scored, key=lambda item: (-item[0], item[1]))]


def evaluate(path: Path, *, k: int = 5) -> dict[str, float | int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates = [
        Candidate(
            id=str(row["id"]),
            text=str(row["text"]),
            kind=str(row.get("kind") or "semantic"),
            importance=int(row.get("importance") or 3),
        )
        for row in payload["memories"]
    ]
    queries = payload["queries"]
    hits = 0
    reciprocal_sum = 0.0
    for query in queries:
        ranked = _rank_candidates(str(query["text"]), candidates)
        expected = str(query["expected_id"])
        top_k = ranked[:k]
        if expected in top_k:
            hits += 1
            reciprocal_sum += 1.0 / (ranked.index(expected) + 1)
    total = max(1, len(queries))
    return {
        "queries": len(queries),
        f"recall_at_{k}": round(hits / total, 4),
        "mrr": round(reciprocal_sum / total, 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Mia memory RAG ranking on a sanitized golden corpus.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    result = evaluate(args.corpus, k=max(1, args.k))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
