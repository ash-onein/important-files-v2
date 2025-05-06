from rank_bm25 import BM25Okapi # type: ignore
from typing import List

def bm25_rerank_matches(matches: List[dict], query: str) -> List[dict]:
    if not matches:
        return []

    # Use entity_name + context or description as corpus
    documents = [
        (match["entity_name"] + " " + match.get("context", "")) for match in matches
    ]
    tokenized_corpus = [doc.lower().split() for doc in documents]
    tokenized_query = query.lower().split()

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    # Attach scores to matches and sort
    for match, score in zip(matches, scores):
        match["bm25_score"] = score

    return sorted(matches, key=lambda x: x["bm25_score"], reverse=True)    