from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    score: float
    level: str
    label: str
    needs_review: bool


def compute_confidence(
    law_count: int,
    case_count: int,
    court_count: int,
    is_well_formed: bool,
    completeness_score: float = 1.0,
    gap_count: int = 0,
) -> ConfidenceResult:
    score = 0.0
    score += min(law_count, 6) * 0.10
    score += min(case_count, 5) * 0.07
    score += min(court_count, 3) * 0.06
    if is_well_formed:
        score += 0.20
    if law_count >= 2:
        score += 0.10
    if case_count >= 1 or court_count >= 1:
        score += 0.08
    score += completeness_score * 0.15
    score -= min(gap_count * 0.04, 0.20)

    score = min(max(round(score, 2), 0.0), 1.0)

    if score >= 0.72 and gap_count <= 1:
        level, label = "high", "High confidence"
        needs_review = False
    elif score >= 0.45:
        level, label = "medium", "Moderate confidence — verify noted gaps"
        needs_review = gap_count >= 3
    else:
        level, label = "low", "Limited sources — attorney review required"
        needs_review = True

    return ConfidenceResult(score=score, level=level, label=label, needs_review=needs_review)
