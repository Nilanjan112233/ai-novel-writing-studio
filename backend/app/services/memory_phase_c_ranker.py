"""Replay-safe Phase C lexical, metadata, graph, and fusion ranking helpers.

These functions rank already-derived memory. They do not decide authority or
eligibility; callers must apply the P0 policy before invoking them.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List

PHASE_C_RANKER_VERSION = 1
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "did",
    "do", "does", "for", "from", "had", "has", "have", "he", "her", "hers",
    "him", "his", "i", "in", "into", "is", "it", "its", "me", "my", "of",
    "on", "or", "our", "she", "that", "the", "their", "them", "they", "this",
    "to", "was", "we", "were", "what", "when", "where", "which", "who", "why",
    "with", "you", "your", "now", "currently", "current", "chapter", "story",
}
SYNONYM_GROUPS = (
    {"hand", "palm"}, {"injury", "injured", "wound", "burned", "burn", "scar", "aches"},
    {"water", "river"}, {"road", "path", "route"}, {"submerged", "drowned", "underwater"},
    {"map", "maps", "cartographer"}, {"understands", "reads", "read"},
    {"old", "past", "earlier", "historical"}, {"held", "holds", "owner", "owns", "possesses"},
)


def lexical_terms(text: str, *, include_bigrams: bool = True) -> List[str]:
    raw = re.findall(r"[a-z0-9][a-z0-9'_-]*", str(text or "").lower())
    unigrams = [token for token in raw if len(token) >= 2 and token not in STOP_WORDS]
    result = list(dict.fromkeys(unigrams))
    if include_bigrams:
        result.extend(
            f"{left} {right}"
            for left, right in zip(raw, raw[1:])
            if left not in STOP_WORDS and right not in STOP_WORDS
        )
    return list(dict.fromkeys(result))[:160]


def lexical_document_fields(content: str) -> Dict[str, Any]:
    tokens = re.findall(r"[a-z0-9][a-z0-9'_-]*", str(content or "").lower())
    searchable = lexical_terms(content)
    frequencies = Counter(token for token in tokens if token not in STOP_WORDS)
    return {
        "search_terms": searchable,
        "term_frequencies": {term: min(int(count), 20) for term, count in frequencies.items()},
        "document_length": max(1, len(tokens)),
        "phase_c_ranker_version": PHASE_C_RANKER_VERSION,
    }


def expanded_query_terms(text: str) -> List[str]:
    base = lexical_terms(text, include_bigrams=False)
    expanded = list(base)
    base_set = set(base)
    for group in SYNONYM_GROUPS:
        if base_set & group:
            expanded.extend(sorted(group))
    return list(dict.fromkeys(expanded))[:80]


def select_discriminative_terms(query: str, document_frequencies: Dict[str, int], total_documents: int) -> List[str]:
    """Choose rare query terms without silently truncating matching documents."""
    available = [(term, int(document_frequencies.get(term) or 0)) for term in expanded_query_terms(query)]
    available = [(term, count) for term, count in available if count > 0]
    if not available:
        return []
    threshold = max(24, int(total_documents * 0.08))
    rare = sorted((item for item in available if item[1] <= threshold), key=lambda item: (item[1], item[0]))
    selected = rare[:6]
    if not selected:
        selected = sorted(available, key=lambda item: (item[1], item[0]))[:2]
    return [term for term, _count in selected]


def story_candidate_domain(query: str) -> set[str] | None:
    terms = set(expanded_query_terms(query))
    if terms & {"know", "knows", "knowledge", "alive"}:
        return {"knowledge"}
    if terms & {"owner", "owns", "held", "holds", "possesses"}:
        return {"artifact", "owner"}
    if terms & {"mystery", "clue", "unresolved", "secret", "reveal"}:
        return {"mystery", "plot_thread", "open_obligation", "mystery_state", "mystery_truth"}
    if terms & {"relationship", "trust", "distrust", "alliance"}:
        return {"relationship", "relationship_state", "relationship_observation"}
    return None


def matches_story_domain(document: Dict[str, Any], domain: set[str] | None) -> bool:
    if not domain:
        return True
    metadata = document.get("metadata") or {}
    return str(document.get("source_type") or "") in domain or str(metadata.get("predicate") or "") in domain


def bm25_scores(query: str, documents: List[Dict[str, Any]]) -> Dict[str, float]:
    """BM25 over an identical replay population; no external search service."""
    query_terms = expanded_query_terms(query)
    if not query_terms or not documents:
        return {}
    lengths = [int(doc.get("document_length") or len(lexical_terms(doc.get("content") or "", include_bigrams=False)) or 1) for doc in documents]
    avgdl = sum(lengths) / len(lengths)
    doc_terms: List[Counter[str]] = []
    df: Counter[str] = Counter()
    for doc in documents:
        frequencies = doc.get("term_frequencies")
        terms = Counter(frequencies) if isinstance(frequencies, dict) else Counter(re.findall(r"[a-z0-9][a-z0-9'_-]*", str(doc.get("content") or "").lower()))
        doc_terms.append(terms)
        for term in set(query_terms) & set(terms):
            df[term] += 1
    scores: Dict[str, float] = {}
    total = len(documents)
    k1, b = 1.5, 0.72
    for doc, length, terms in zip(documents, lengths, doc_terms):
        score = 0.0
        for term in query_terms:
            tf = float(terms.get(term) or 0)
            if not tf:
                continue
            idf = math.log(1.0 + (total - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * length / max(avgdl, 1.0)))
        scores[str(doc.get("logical_identity") or doc.get("source_id") or doc.get("_id"))] = score
    return scores


def hash_scores(query: str, documents: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    # Local import avoids making the production retrieval module and the pure
    # bake-off helpers depend on each other at import time.
    from app.services.memory_retrieval_service import _cosine, embed_text

    query_vector = embed_text(query)
    return {
        str(doc.get("logical_identity") or doc.get("source_id") or doc.get("_id")): _cosine(query_vector, doc.get("embedding") or embed_text(str(doc.get("content") or "")))
        for doc in documents
    }


def story_metadata_score(query: str, document: Dict[str, Any], *, as_of_chapter: int | None = None) -> float:
    terms = set(lexical_terms(query, include_bigrams=False))
    metadata = document.get("metadata") or {}
    content_terms = set(lexical_terms(str(document.get("content") or ""), include_bigrams=False))
    entity_values = [
        metadata.get("subject"), metadata.get("compact_value"),
        *(metadata.get("entity_refs") or []), *(metadata.get("known_by") or []),
    ]
    entity_terms = set(lexical_terms(" ".join(str(value or "") for value in entity_values), include_bigrams=False))
    source_type = str(document.get("source_type") or "")
    predicate = str(metadata.get("predicate") or "")
    score = min(len(terms & entity_terms) * 0.55, 2.2)
    score += min(len(terms & content_terms) * 0.08, 0.48)
    if terms & {"clue", "mystery", "unresolved", "reveal", "secret"} and source_type in {"mystery", "plot_thread", "foreshadow_v2", "atomic_memory"}:
        score += 0.8
    if terms & {"promise", "obligation", "callback", "unresolved", "remain"} and (source_type in {"plot_thread", "foreshadow_v2", "atomic_memory"} or predicate in {"open_obligation", "plot_thread_state", "mystery_state"}):
        score += 0.75
    if terms & {"relationship", "trust", "distrust", "alliance"} and (source_type == "relationship" or "relationship" in predicate):
        score += 0.7
    if terms & {"know", "knows", "knowledge"} and (source_type == "knowledge" or predicate == "knowledge"):
        score += 0.8
    if terms & {"owner", "owns", "held", "holds", "has"} and (source_type == "artifact" or predicate == "owner"):
        score += 0.85
    status = str(metadata.get("status") or "").lower()
    if status in {"open", "unresolved", "active"} and terms & {"open", "unresolved", "remain", "next"}:
        score += 0.45
    chapter = metadata.get("chapter_number") or metadata.get("valid_from_chapter")
    if as_of_chapter is not None and chapter is not None:
        distance = max(0, int(as_of_chapter) - int(chapter))
        score += max(0.0, 0.12 - min(distance, 120) * 0.001)
    confidence = float(metadata.get("quality_score") or metadata.get("confidence") or 0.0)
    score += min(confidence, 1.0) * 0.1
    return score


def graph_proximity_scores(query: str, documents: Iterable[Dict[str, Any]], nodes: Iterable[Dict[str, Any]], edges: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    query_terms = set(lexical_terms(query, include_bigrams=False))
    node_by_id = {str(node.get("node_id")): node for node in nodes}
    seeds = {
        node_id for node_id, node in node_by_id.items()
        if query_terms & set(lexical_terms(str(node.get("label") or ""), include_bigrams=False))
    }
    neighbors: Dict[str, int] = {node_id: 0 for node_id in seeds}
    for edge in edges:
        source, target = str(edge.get("source") or ""), str(edge.get("target") or "")
        if source in seeds: neighbors[target] = min(neighbors.get(target, 99), 1)
        if target in seeds: neighbors[source] = min(neighbors.get(source, 99), 1)
    labels = [(set(lexical_terms(str(node_by_id[node_id].get("label") or ""), include_bigrams=False)), distance) for node_id, distance in neighbors.items() if node_id in node_by_id]
    result = {}
    for doc in documents:
        doc_terms = set(lexical_terms(str(doc.get("content") or ""), include_bigrams=False))
        score = sum((0.45 if distance == 0 else 0.18) for label_terms, distance in labels if label_terms & doc_terms)
        result[str(doc.get("logical_identity") or doc.get("source_id") or doc.get("_id"))] = min(score, 1.2)
    return result


def rank_from_scores(documents: List[Dict[str, Any]], scores: Dict[str, float]) -> List[Dict[str, Any]]:
    return sorted(documents, key=lambda doc: (scores.get(str(doc.get("logical_identity") or doc.get("source_id") or doc.get("_id")), 0.0), -int(doc.get("estimated_tokens") or 0)), reverse=True)


def reciprocal_rank_fusion(rankings: List[List[Dict[str, Any]]], *, k: int = 60, weights: List[float] | None = None) -> Dict[str, float]:
    fused: Dict[str, float] = defaultdict(float)
    weights = weights or [1.0] * len(rankings)
    for ranking, weight in zip(rankings, weights):
        for rank, doc in enumerate(ranking, 1):
            key = str(doc.get("logical_identity") or doc.get("source_id") or doc.get("_id"))
            fused[key] += float(weight) / (k + rank)
    return dict(fused)
