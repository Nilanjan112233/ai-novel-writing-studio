"""Deterministic prose quality signals used by editorial and story audits."""
from __future__ import annotations

import re
from collections import Counter
from statistics import mean, pstdev
from typing import Any, Dict, Iterable


AI_PHRASES = (
    "in that moment",
    "a mix of",
    "could not help but",
    "the weight of",
    "a testament to",
    "it was as if",
    "seemed to",
    "felt a surge",
    "for what felt like",
    "little did",
)
EXPLANATORY_PHRASES = (
    "because of this",
    "this meant that",
    "in other words",
    "the reason was",
    "which meant",
    "as a result",
    "this was why",
)
EMOTIONAL_LABELS = (
    "felt sad",
    "felt angry",
    "felt afraid",
    "felt relieved",
    "felt guilty",
    "was heartbroken",
    "was devastated",
)


def _sentences(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+", text.strip())
        if item.strip()
    ]


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


def _finding(
    category: str,
    message: str,
    *,
    severity: str = "warning",
    evidence: Iterable[str] = (),
) -> Dict[str, Any]:
    return {
        "category": category,
        "severity": severity,
        "message": message,
        "evidence": list(evidence),
    }


def analyze_text(text: str) -> Dict[str, Any]:
    """Return findings only; this service never rewrites prose."""
    normalized = str(text or "").strip()
    sentences = _sentences(normalized)
    words = _words(normalized)
    findings: list[Dict[str, Any]] = []
    lower = normalized.lower()

    phrase_hits = {
        phrase: lower.count(phrase)
        for phrase in AI_PHRASES
        if lower.count(phrase)
    }
    if sum(phrase_hits.values()) >= 3:
        findings.append(
            _finding(
                "ai_writing_fingerprint",
                "Several familiar synthetic-prose phrases recur in the same passage.",
                evidence=[
                    f"{phrase}: {count}"
                    for phrase, count in phrase_hits.items()
                ],
            )
        )

    explanation_hits = {
        phrase: lower.count(phrase)
        for phrase in EXPLANATORY_PHRASES
        if lower.count(phrase)
    }
    if sum(explanation_hits.values()) >= 3:
        findings.append(
            _finding(
                "excessive_exposition",
                "The prose repeatedly explains implications instead of leaving room for inference.",
                evidence=list(explanation_hits),
            )
        )

    emotional_hits = {
        phrase: lower.count(phrase)
        for phrase in EMOTIONAL_LABELS
        if lower.count(phrase)
    }
    if sum(emotional_hits.values()) >= 3:
        findings.append(
            _finding(
                "emotional_over_explanation",
                "Emotions are labeled repeatedly instead of emerging through behavior and contradiction.",
                evidence=list(emotional_hits),
            )
        )

    openings = []
    for sentence in sentences:
        opening = " ".join(_words(sentence)[:3])
        if opening:
            openings.append(opening)
    repeated_openings = [
        opening for opening, count in Counter(openings).items() if count >= 3
    ]
    if repeated_openings:
        findings.append(
            _finding(
                "repetitive_sentence_pattern",
                "Multiple sentences begin with the same grammatical shape.",
                evidence=repeated_openings[:6],
            )
        )

    lengths = [len(_words(sentence)) for sentence in sentences if _words(sentence)]
    if len(lengths) >= 8 and mean(lengths) >= 8 and pstdev(lengths) < 2.5:
        findings.append(
            _finding(
                "over_polished_rhythm",
                "Sentence lengths are unusually uniform, which can make the prose feel manufactured.",
                evidence=[
                    f"average={mean(lengths):.1f}",
                    f"standard_deviation={pstdev(lengths):.1f}",
                ],
            )
        )

    paragraphs = [
        item.strip() for item in re.split(r"\n\s*\n", normalized) if item.strip()
    ]
    paragraph_lengths = [len(_words(item)) for item in paragraphs]
    if (
        len(paragraph_lengths) >= 5
        and mean(paragraph_lengths) >= 20
        and pstdev(paragraph_lengths) < 6
    ):
        findings.append(
            _finding(
                "repetitive_paragraph_structure",
                "Paragraphs are consistently similar in size, suggesting a repeated structural template.",
            )
        )

    dialogue = re.findall(r'["“](.*?)["”]', normalized, flags=re.DOTALL)
    dialogue_openings = [
        " ".join(_words(fragment)[:4]) for fragment in dialogue if _words(fragment)
    ]
    repeated_dialogue = [
        value
        for value, count in Counter(dialogue_openings).items()
        if count >= 3
    ]
    if repeated_dialogue:
        findings.append(
            _finding(
                "repetitive_dialogue_pattern",
                "Dialogue lines repeatedly use the same opening pattern.",
                evidence=repeated_dialogue[:6],
            )
        )

    clean_resolution_terms = (
        "everything made sense",
        "at last, they understood",
        "all was forgiven",
        "the misunderstanding was over",
        "finally at peace",
    )
    clean_hits = [term for term in clean_resolution_terms if term in lower]
    if clean_hits:
        findings.append(
            _finding(
                "overly_clean_resolution",
                "The passage signals a fully resolved emotional outcome with little remaining ambiguity.",
                evidence=clean_hits,
            )
        )

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "findings": findings,
        "fingerprint_count": sum(
            1
            for item in findings
            if item["category"] == "ai_writing_fingerprint"
        ),
    }


def compare_chapters(chapters: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Detect repeated chapter-level shapes without reading unrelated projects."""
    ordered = sorted(
        list(chapters),
        key=lambda item: int(item.get("chapter_number") or 0),
    )
    findings: list[Dict[str, Any]] = []
    signatures: Counter[tuple[int, int, int, int]] = Counter()
    opening_phrases: Counter[str] = Counter()
    word_counts = []
    for chapter in ordered:
        word_counts.append(int(chapter.get("word_count") or 0))
        signatures[
            (
                len(chapter.get("important_events") or []),
                len(chapter.get("character_changes") or []),
                len(chapter.get("knowledge_revealed") or []),
                len(chapter.get("future_obligations") or []),
            )
        ] += 1
        summary_words = _words(str(chapter.get("chapter_summary") or ""))
        if summary_words:
            opening_phrases[" ".join(summary_words[:4])] += 1

    repeated_shapes = [
        signature for signature, count in signatures.items() if count >= 4
    ]
    if repeated_shapes:
        findings.append(
            _finding(
                "repetitive_chapter_structure",
                "Four or more chapters share the same event/change/reveal/obligation shape.",
                evidence=[str(item) for item in repeated_shapes[:6]],
            )
        )
    repeated_openings = [
        phrase for phrase, count in opening_phrases.items() if count >= 3
    ]
    if repeated_openings:
        findings.append(
            _finding(
                "repetitive_chapter_opening",
                "Chapter summaries repeatedly begin with the same structural phrase.",
                evidence=repeated_openings[:6],
            )
        )
    nonzero = [count for count in word_counts if count]
    if len(nonzero) >= 8 and mean(nonzero) > 500 and pstdev(nonzero) < mean(nonzero) * 0.08:
        findings.append(
            _finding(
                "over_uniform_chapter_length",
                "Chapter lengths vary by less than eight percent across a long run.",
                evidence=[
                    f"average={mean(nonzero):.0f}",
                    f"standard_deviation={pstdev(nonzero):.0f}",
                ],
            )
        )
    return findings


story_quality_service = type(
    "StoryQualityService",
    (),
    {
        "analyze_text": staticmethod(analyze_text),
        "compare_chapters": staticmethod(compare_chapters),
    },
)()
