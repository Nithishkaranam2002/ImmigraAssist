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
) -> ConfidenceResult:
    score = 0.0
    score += min(law_count, 4) * 0.12
    score += min(case_count, 4) * 0.08
    score += min(court_count, 3) * 0.08
    if is_well_formed:
        score += 0.25
    if law_count >= 2 and case_count >= 1:
        score += 0.15

    score = min(round(score, 2), 1.0)

    if score >= 0.75:
        level, label = "high", "High confidence"
        needs_review = False
    elif score >= 0.45:
        level, label = "medium", "Moderate confidence"
        needs_review = False
    else:
        level, label = "low", "Limited sources"
        needs_review = True

    return ConfidenceResult(score=score, level=level, label=label, needs_review=needs_review)
