import re
from dataclasses import dataclass, field

from app.llm.response_parser import ParsedResponse


@dataclass
class QualityAssessment:
    parsed: ParsedResponse
    gaps: list[str] = field(default_factory=list)
    completeness_score: float = 1.0
    source_summary: str = ""


# Topic-specific material facts attorneys expect in research memos
_TOPIC_CHECKS: list[tuple[re.Pattern, list[str], list[str]]] = [
    (
        re.compile(r"\b(cap|lottery|registration)\b", re.I),
        re.compile(r"\bh[-\s]?1b\b", re.I),
        [
            "annual numerical cap (65,000 regular + 20,000 master's exemption)",
            "electronic registration period and fee",
            "selection/lottery process (including any wage-weighting if applicable)",
            "petition filing window after selection",
            "earliest employment start date (typically October 1 of the fiscal year)",
        ],
    ),
    (
        re.compile(r"\b(eligib|require|qualif)\b", re.I),
        re.compile(r"\b(ead|work\s+auth|employment\s+auth)\b", re.I),
        [
            "eligibility criteria (who qualifies)",
            "required forms and filing category",
            "supporting evidence typically required",
            "timing restrictions or dependencies on principal's status",
        ],
    ),
    (
        re.compile(r"\b(compare|difference|vs\.?|versus)\b", re.I),
        re.compile(r".", re.I),
        [
            "side-by-side comparison of eligibility",
            "key procedural differences",
            "employer/sponsor requirements for each option",
        ],
    ),
]


def _answer_lower(answer: str) -> str:
    return answer.lower().replace(",", "")


def assess_and_enhance(
    *,
    parsed: ParsedResponse,
    query: str,
    visa_type: str | None,
    law_count: int,
    case_count: int,
    court_count: int,
) -> QualityAssessment:
    """Flag missing sections and topic-specific gaps; enrich notes for attorneys."""
    gaps: list[str] = []
    answer = parsed.answer or ""
    answer_l = _answer_lower(answer)

    # Structural completeness
    if not parsed.next_steps:
        gaps.append("Next steps section missing — define client/employer follow-up actions.")
    elif len(parsed.next_steps) < 3:
        gaps.append("Next steps may be incomplete — confirm all filing and verification tasks.")

    if not parsed.risks:
        gaps.append("Risks & considerations not listed — review denial scenarios and deadlines manually.")

    if not parsed.related_forms and visa_type:
        gaps.append(
            f"Related forms not listed — verify standard USCIS forms for {visa_type.upper()}."
        )

    if not parsed.important_notes:
        gaps.append("No important notes/caveats captured — verify date-sensitive policy manually.")

    if law_count == 0:
        gaps.append("No law/policy sources retrieved — answer may rely on limited context.")
    if case_count == 0 and court_count == 0:
        gaps.append("No case precedents retrieved — confirm whether case law is relevant.")

    # Topic-specific material-fact checks
    for query_pat, topic_pat, expected_facts in _TOPIC_CHECKS:
        if not query_pat.search(query):
            continue
        if topic_pat.pattern != "." and not topic_pat.search(query):
            continue
        for fact in expected_facts:
            # Heuristic: check if key concepts from expected fact appear in answer
            tokens = [t for t in re.split(r"[^a-z0-9]+", fact.lower()) if len(t) > 3]
            hits = sum(1 for t in tokens[:6] if t in answer_l)
            if hits < 2:
                gaps.append(f"Answer may not fully cover: {fact}.")

    # H-1B cap numbers — common omission
    if re.search(r"\bh[-\s]?1b\b", query, re.I) and re.search(r"\b(cap|lottery)\b", query, re.I):
        if "65000" not in answer_l and "65 000" not in answer_l and "65,000" not in answer.lower():
            gaps.append(
                "Standard H-1B cap figures (65,000 regular + 20,000 master's cap) "
                "not clearly stated — verify on USCIS H-1B cap season page."
            )

    completeness = 1.0
    completeness -= min(len(gaps) * 0.08, 0.5)
    if not parsed.is_well_formed:
        completeness -= 0.2
        gaps.insert(0, "Response format was incomplete — verify all sections in source material.")

    source_parts = []
    if law_count:
        source_parts.append(f"{law_count} policy source{'s' if law_count != 1 else ''}")
    if case_count:
        source_parts.append(f"{case_count} case precedent{'s' if case_count != 1 else ''}")
    if court_count:
        source_parts.append(f"{court_count} court decision{'s' if court_count != 1 else ''}")
    source_summary = ", ".join(source_parts) if source_parts else "limited sources"

    enhanced_notes = list(parsed.important_notes)
    for gap in gaps:
        if gap not in enhanced_notes:
            enhanced_notes.append(gap)

    enhanced = ParsedResponse(
        answer=parsed.answer,
        cited_laws=parsed.cited_laws,
        cited_cases=parsed.cited_cases,
        important_notes=enhanced_notes,
        next_steps=parsed.next_steps,
        risks=parsed.risks,
        related_forms=parsed.related_forms,
        raw_content=parsed.raw_content,
        is_well_formed=parsed.is_well_formed,
    )

    return QualityAssessment(
        parsed=enhanced,
        gaps=gaps,
        completeness_score=max(round(completeness, 2), 0.0),
        source_summary=source_summary,
    )
