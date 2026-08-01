"""
Real, deterministic SEO analysis of content text - no external API needed.

Computes an approximate Flesch Reading Ease score for readability, keyword
density against the ideal 1-3% range, and a structure score from paragraph
count and title/summary presence.
"""

import re
from typing import Any, Dict, List, Optional


def _count_syllables(word: str) -> int:
    word = word.lower().strip(".,!?;:\"'()")
    if not word:
        return 0
    vowel_groups = re.findall(r"[aeiouy]+", word)
    count = len(vowel_groups)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def _sentences(text: str) -> List[str]:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    return sentences or [text]


def analyze(
    body: str,
    title: str,
    summary: Optional[str] = None,
    primary_keyword: Optional[str] = None,
) -> Dict[str, Any]:
    words = re.findall(r"[A-Za-z']+", body)
    word_count = len(words) or 1
    sentences = _sentences(body)
    sentence_count = len(sentences) or 1
    syllable_count = sum(_count_syllables(w) for w in words) or word_count

    # Approximate Flesch Reading Ease, clamped to 0-100.
    flesch = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
    readability_score = max(0, min(100, round(flesch)))

    keyword_density_score = 50  # neutral default when there's no keyword to check
    if primary_keyword:
        occurrences = len(re.findall(re.escape(primary_keyword.lower()), body.lower()))
        density = (occurrences / word_count) * 100
        if 1.0 <= density <= 3.0:
            keyword_density_score = 100
        elif density == 0:
            keyword_density_score = 0
        elif density < 1.0:
            keyword_density_score = round(density * 100)
        else:  # keyword stuffing
            keyword_density_score = max(0, round(100 - (density - 3.0) * 20))

    paragraphs = [p for p in body.split("\n\n") if p.strip()]
    structure_score = min(100, len(paragraphs) * 15 + (20 if title else 0) + (10 if summary else 0))

    overall_score = round((readability_score + keyword_density_score + structure_score) / 3)

    recommendations = []
    if readability_score < 50:
        recommendations.append("Content is hard to read - use shorter sentences and simpler words.")
    if primary_keyword and keyword_density_score < 50:
        recommendations.append(f"Keyword '{primary_keyword}' density is too low - mention it more naturally.")
    if primary_keyword and keyword_density_score < 100 and "stuffing" not in " ".join(recommendations):
        occurrences = len(re.findall(re.escape(primary_keyword.lower()), body.lower()))
        if (occurrences / word_count) * 100 > 3.0:
            recommendations.append(f"Keyword '{primary_keyword}' appears too often - risk of keyword stuffing.")
    if len(paragraphs) < 3:
        recommendations.append("Add more paragraphs to improve structure and scannability.")
    if not summary:
        recommendations.append("Add a summary to use as the meta description.")
    if not recommendations:
        recommendations.append("Looks good - no major SEO issues found.")

    return {
        "overall_score": overall_score,
        "readability_score": readability_score,
        "keyword_density_score": keyword_density_score,
        "structure_score": structure_score,
        "meta_title": title[:60],
        "meta_description": (summary or body)[:160],
        "primary_keyword": primary_keyword,
        "recommendations": recommendations,
    }
