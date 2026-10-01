"""Provider-free Phase C ranking/candidate-generation bake-off."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT))

from app.services.memory_phase_c_ranker import (  # noqa: E402
    bm25_scores, expanded_query_terms, graph_proximity_scores, hash_scores, lexical_document_fields,
    lexical_terms, matches_story_domain, rank_from_scores, reciprocal_rank_fusion, select_discriminative_terms, story_candidate_domain, story_metadata_score,
)
from app.services.memory_retrieval_policy import RetrievalEligibilityContext, retrieval_eligibility_policy  # noqa: E402
from app.services.memory_retrieval_service import narrative_relevance_score  # noqa: E402
from scripts.run_memory_phase_b_scale import _seed  # noqa: E402
from bson import ObjectId  # noqa: E402

SCALES = (10, 25, 50, 100, 250, 500)


def _extra(pid: ObjectId, chapters: int) -> list[dict[str, Any]]:
    from scripts.run_memory_phase_b_scale import _indexed
    midpoint = max(3, chapters // 2)
    rows = [
        ("character", "seraphine", "Seraphine Quill is the only cartographer who can read drowned roads.", {"logical_source_id": "seraphine", "authority_level": "structured_owner", "valid_from_chapter": 1}),
        ("world", "virelai", "Virelai Observatory stands above the salt marsh and tracks the black moon.", {"logical_source_id": "virelai", "authority_level": "structured_owner", "valid_from_chapter": 1}),
        ("world", "river-path-rule", "The third bell opens the river path for seven breaths.", {"logical_source_id": "river-path-rule", "authority_level": "confirmed_planning", "valid_from_chapter": 1}),
        ("plot_thread", "broken-bell-promise", "Promise: Return the broken bell to Mara before the thaw.", {"logical_source_id": "broken-bell-promise", "authority_level": "confirmed_planning", "status": "open", "valid_from_chapter": 5}),
        ("mystery", "owed-clue", "Quoted clue: What is owed is not forgotten.", {"logical_source_id": "owed-clue", "authority_level": "structured_owner", "status": "open", "valid_from_chapter": 1}),
        ("atomic_memory", "ferryman-injury", "Mara: Her left palm was burned by the ferryman's seal and still aches in rain.", {"logical_source_id": "ferryman-injury", "authority_level": "derived", "subject": "Mara", "predicate": "character_change", "entity_refs": ["Mara", "ferryman seal"], "confidence": 0.94, "valid_from_chapter": 5}),
        ("mystery", "black-moon", "Why does the black moon erase reflections? The clue remains unresolved.", {"logical_source_id": "black-moon", "authority_level": "structured_owner", "status": "open", "valid_from_chapter": 25 if chapters >= 25 else 1}),
        ("plot_thread", "chapter-one-callback", "Long-range callback: Mara must answer the knock heard beneath the Chapter 1 funeral bell.", {"logical_source_id": "chapter-one-callback", "authority_level": "structured_owner", "status": "open", "valid_from_chapter": 1}),
        ("artifact", "northglass-historical", "Northglass is held by Mara.", {"logical_source_id": "northglass-state", "owner_source_version": 1, "authority_level": "confirmed_planning", "valid_from_chapter": 3, "valid_to_chapter": 7}),
        ("artifact", "northglass-current", "Northglass is held by Ivo.", {"logical_source_id": "northglass-state", "owner_source_version": 2, "authority_level": "confirmed_planning", "valid_from_chapter": 8}),
        ("knowledge", "elias-private", "Elias is alive in the eastern tower.", {"logical_source_id": "elias-private", "authority_level": "confirmed_planning", "valid_from_chapter": midpoint, "known_by": ["Ivo"], "not_known_by": ["Mara"]}),
        ("timeline", "rejected-elias", "Maybe Elias is secretly the villain.", {"logical_source_id": "rejected-elias", "status": "rejected", "valid_from_chapter": 1}),
    ]
    result = []
    for source_type, source_id, content, metadata in rows:
        metadata = {**metadata, "source_type": source_type, "physical_source_id": source_id, "logical_identity": f"{source_type}:{metadata['logical_source_id']}:v{metadata.get('owner_source_version', 1)}"}
        row = _indexed(pid, source_type, metadata["logical_source_id"], content, metadata)
        row.update(lexical_document_fields(content)); row["logical_identity"] = metadata["logical_identity"]; row["estimated_tokens"] = max(1, len(content) // 4)
        result.append(row)
    return result


def _documents(chapters: int) -> list[dict[str, Any]]:
    pid = ObjectId(); _atomics, _episodes, rows = _seed(pid, chapters)
    for row in rows:
        row.update(lexical_document_fields(row["content"])); row["logical_identity"] = (row.get("metadata") or {}).get("logical_identity") or f"{row['source_type']}:{row['source_id']}:v{row.get('source_version', 1)}"; row["estimated_tokens"] = max(1, len(row["content"]) // 4)
    return [*rows, *_extra(pid, chapters)]


def _queries(chapters: int) -> list[dict[str, Any]]:
    midpoint = max(3, chapters // 2)
    return [
        {"id": "rare_artifact", "q": f"Asterlock-{chapters} drowned archive", "expected": f"asterlock-{chapters}", "kind": "exact", "as_of": chapters, "pov": "Mara"},
        {"id": "rare_character", "q": "Who is Seraphine Quill?", "expected": "seraphine", "kind": "exact", "as_of": chapters},
        {"id": "unique_place", "q": "Where is Virelai Observatory?", "expected": "virelai", "kind": "exact", "as_of": chapters},
        {"id": "exact_promise", "q": "Return the broken bell to Mara before the thaw", "expected": "broken-bell-promise", "kind": "exact", "as_of": chapters},
        {"id": "quoted_clue", "q": "What is owed is not forgotten", "expected": "owed-clue", "kind": "exact", "as_of": chapters},
        {"id": "injury_paraphrase", "q": "What old injury still affects Mara's hand?", "expected": "ferryman-injury", "kind": "paraphrase", "as_of": chapters, "pov": "Mara"},
        {"id": "rule_paraphrase", "q": "How can someone enter the water road?", "expected": "river-path-rule", "kind": "paraphrase", "as_of": chapters},
        {"id": "cartographer_paraphrase", "q": "Who understands maps of submerged routes?", "expected": "seraphine", "kind": "paraphrase", "as_of": chapters},
        {"id": "old_callback", "q": "Which unresolved funeral-bell callback from the opening still matters?", "expected": "chapter-one-callback", "kind": "long_range", "as_of": chapters},
        {"id": "open_mystery", "q": "What unresolved clue about reflections matters next?", "expected": "black-moon", "kind": "mystery", "as_of": chapters},
        {"id": "ownership_history", "q": "Who held Northglass in Chapter 5?", "expected": "northglass-state", "contains": "Mara", "kind": "temporal", "as_of": 5},
        {"id": "ownership_current", "q": "Who has Northglass now?", "expected": "northglass-state", "contains": "Ivo", "kind": "temporal", "as_of": max(10, chapters)},
        {"id": "ivo_knowledge", "q": "What does Ivo know about Elias?", "expected": "elias-private", "kind": "knowledge", "as_of": max(midpoint, 10), "pov": "Ivo"},
        {"id": "mara_knowledge", "q": "What does Mara know about Elias being alive?", "expected": None, "forbidden": "elias-private", "kind": "knowledge", "as_of": max(midpoint, 10), "pov": "Mara"},
        {"id": "rejected_history", "q": "What did I reject about Elias?", "expected": "rejected-elias", "kind": "story_studio", "as_of": chapters, "safe": False},
    ]


def _eligible(documents, case):
    context = RetrievalEligibilityContext(safe_for_writing=case.get("safe", True), consumer="phase_c_bakeoff", as_of_chapter=case.get("as_of"), pov_character=case.get("pov"))
    return [doc for doc in documents if retrieval_eligibility_policy.evaluate(doc, context).eligible]


def _normalize(scores):
    if not scores: return {}
    values = list(scores.values()); lo, hi = min(values), max(values)
    if hi <= lo: return {key: 0.0 for key in scores}
    return {key: (value - lo) / (hi - lo) for key, value in scores.items()}


def _rank_methods(case, docs, semantic_scores=None, nodes=None, edges=None):
    query = case["q"]; started = time.perf_counter(); hs = hash_scores(query, docs); hash_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter(); ls = bm25_scores(query, docs); lexical_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter(); ms = {str(doc["logical_identity"]): story_metadata_score(query, doc, as_of_chapter=case.get("as_of")) for doc in docs}; metadata_ms = (time.perf_counter() - started) * 1000
    gs = graph_proximity_scores(query, docs, nodes or [], edges or [])
    phase_b_scores = {}
    for doc in docs:
        key = str(doc["logical_identity"]); phase_b_scores[key] = narrative_relevance_score(query, doc, hs[key])
    expanded = expanded_query_terms(query); domain = story_candidate_domain(query)
    domain_docs = [doc for doc in docs if matches_story_domain(doc, domain)] if domain else docs
    frequencies = {term: sum(1 for doc in domain_docs if term in set(doc.get("search_terms") or [])) for term in expanded}
    selected_terms = set(select_discriminative_terms(query, frequencies, len(domain_docs)))
    lexical_candidates = [doc for doc in domain_docs if selected_terms & set(doc.get("search_terms") or [])]
    if not lexical_candidates and not domain:
        lexical_candidates = docs
    candidate_keys = {doc["logical_identity"] for doc in lexical_candidates}
    fused = {key: 0.48 * _normalize(ls).get(key, 0) + 0.30 * _normalize(hs).get(key, 0) + 0.22 * _normalize(ms).get(key, 0) for key in candidate_keys}
    rankings = {
        "phase_b": (rank_from_scores(docs, phase_b_scores), len(docs), hash_ms),
        "lexical_bm25": (rank_from_scores(docs, ls), len(docs), lexical_ms),
        "hash_vector": (rank_from_scores(docs, hs), len(docs), hash_ms),
        "metadata_story": (rank_from_scores(docs, ms), len(docs), metadata_ms),
        "lexical_metadata_hash": (rank_from_scores(lexical_candidates, fused), len(lexical_candidates), lexical_ms + metadata_ms + (hash_ms * len(lexical_candidates) / max(len(docs), 1))),
    }
    rrf_scores = reciprocal_rank_fusion([rank_from_scores(docs, ls), rank_from_scores(docs, hs), rank_from_scores(docs, ms)], weights=[1.25, 0.8, 1.0])
    rankings["rrf_full"] = (rank_from_scores(docs, rrf_scores), len(docs), lexical_ms + hash_ms + metadata_ms)
    graph_fused = {key: value + 0.10 * gs.get(key, 0) for key, value in fused.items()}
    rankings["fusion_graph"] = (rank_from_scores(lexical_candidates, graph_fused), len(lexical_candidates), lexical_ms + metadata_ms + (hash_ms * len(lexical_candidates) / max(len(docs), 1)))
    if semantic_scores:
        ss = {str(doc["logical_identity"]): semantic_scores.get((case["id"], str(doc["logical_identity"])), 0.0) for doc in docs}
        rankings["semantic_minilm"] = (rank_from_scores(docs, ss), len(docs), 0.0)
        sem_rrf = reciprocal_rank_fusion([rank_from_scores(docs, ls), rank_from_scores(docs, ss), rank_from_scores(docs, ms)], weights=[1.1, 1.0, 1.0])
        rankings["lexical_semantic_metadata_rrf"] = (rank_from_scores(docs, sem_rrf), len(docs), 0.0)
    return rankings, len(lexical_candidates)


def _graph():
    labels = ["Mara", "Elias", "Northglass", "Seraphine Quill", "Virelai Observatory", "Black moon", "River path"]
    nodes = [{"node_id": label.lower().replace(" ", "-"), "label": label} for label in labels]
    edges = [
        {"source": "mara", "target": "elias"}, {"source": "mara", "target": "northglass"},
        {"source": "seraphine-quill", "target": "virelai-observatory"}, {"source": "virelai-observatory", "target": "black-moon"},
        {"source": "northglass", "target": "river-path"},
    ]
    return nodes, edges


def _evaluate(ranking, case):
    expected = case.get("expected"); forbidden = case.get("forbidden")
    ranks = []
    for index, doc in enumerate(ranking[:8], 1):
        source_id = str(doc.get("source_id") or ""); content = str(doc.get("content") or "")
        if expected and (source_id == expected or expected.lower() in content.lower()) and (not case.get("contains") or case["contains"].lower() in content.lower()): ranks.append(index)
    forbidden_hit = any(str(doc.get("source_id") or "") == forbidden for doc in ranking[:8]) if forbidden else False
    return {"rank": ranks[0] if ranks else None, "recall_at_8": 1.0 if (not expected or ranks) else 0.0, "reciprocal_rank": 1.0 / ranks[0] if ranks else (1.0 if not expected and not forbidden_hit else 0.0), "precision_at_8": (1.0 / min(8, len(ranking))) if ranks else 0.0, "unsafe_leakage": int(forbidden_hit), "selected": [str(doc.get("source_id") or "") for doc in ranking[:8]]}


async def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--semantic", action="store_true"); args = parser.parse_args()
    semantic_model = None; semantic_startup_ms = 0; semantic_model_bytes = 0
    if args.semantic:
        before = time.perf_counter()
        from sentence_transformers import SentenceTransformer
        semantic_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True)
        semantic_startup_ms = round((time.perf_counter() - before) * 1000, 3)
        cache = Path.home() / ".cache" / "huggingface" / "hub" / "models--sentence-transformers--all-MiniLM-L6-v2"
        semantic_model_bytes = sum(path.stat().st_size for path in cache.rglob("*") if path.is_file())
    nodes, edges = _graph(); scales = []
    for chapters in SCALES:
        documents = _documents(chapters); cases = _queries(chapters); semantic_scores = {}
        semantic_encode_ms = 0
        if semantic_model:
            texts = [doc["content"] for doc in documents]; queries = [case["q"] for case in cases]
            before = time.perf_counter(); doc_vectors = semantic_model.encode(texts, normalize_embeddings=True, show_progress_bar=False); query_vectors = semantic_model.encode(queries, normalize_embeddings=True, show_progress_bar=False); semantic_encode_ms = round((time.perf_counter() - before) * 1000, 3)
            for case, query_vector in zip(cases, query_vectors):
                for doc, vector in zip(documents, doc_vectors): semantic_scores[(case["id"], doc["logical_identity"])] = float(query_vector @ vector)
        methods: dict[str, list] = defaultdict(list); candidate_counts = []
        for case in cases:
            eligible = _eligible(documents, case); rankings, candidate_count = _rank_methods(case, eligible, semantic_scores, nodes, edges); candidate_counts.append(candidate_count)
            for name, (ranking, scored, latency) in rankings.items(): methods[name].append({"case": case["id"], "kind": case["kind"], "eligible_records": len(eligible), "candidate_count": candidate_count, "records_scored": scored, "latency_ms": round(latency, 3), **_evaluate(ranking, case)})
        aggregates = {}
        for name, rows in methods.items():
            labelled = [row for row in rows if row["case"] != "mara_knowledge"]
            latencies = sorted(row["latency_ms"] for row in rows)
            aggregates[name] = {"recall_at_8": round(statistics.mean(row["recall_at_8"] for row in labelled), 4), "mrr": round(statistics.mean(row["reciprocal_rank"] for row in labelled), 4), "precision_at_8": round(statistics.mean(row["precision_at_8"] for row in labelled), 4), "first_relevant_rank_mean": round(statistics.mean(row["rank"] or 9 for row in labelled), 3), "records_scored_mean": round(statistics.mean(row["records_scored"] for row in rows), 2), "candidate_count_mean": round(statistics.mean(row["candidate_count"] for row in rows), 2), "p50_ms": round(statistics.median(latencies), 3), "p95_ms": round(latencies[max(0, int(len(latencies) * .95) - 1)], 3), "unsafe_leakage": sum(row["unsafe_leakage"] for row in rows), "cases": rows}
        scales.append({"chapters": chapters, "indexed_records": len(documents), "semantic_encode_ms": semantic_encode_ms, "methods": aggregates})
    payload = {"schema_version": 1, "provider_calls": 0, "semantic": {"enabled": bool(semantic_model), "model": "sentence-transformers/all-MiniLM-L6-v2" if semantic_model else None, "startup_ms": semantic_startup_ms, "model_cache_bytes": semantic_model_bytes}, "scales": scales}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8"); print(json.dumps({"output": str(args.output), "semantic": payload["semantic"]}, indent=2))


if __name__ == "__main__": asyncio.run(main())
