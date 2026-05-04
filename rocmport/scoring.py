from __future__ import annotations

from .models import CATEGORIES, SEVERITY_WEIGHTS, Finding, ReadinessScore


def calculate_score(findings: list[Finding], after_patch: bool = False) -> ReadinessScore:
    categories: dict[str, int] = {}
    for category in CATEGORIES:
        penalty = 0
        for finding in findings:
            if finding.category != category:
                continue
            if after_patch and finding.remediable:
                continue
            penalty += SEVERITY_WEIGHTS.get(finding.severity, 10)
        categories[category] = max(0, 100 - penalty)
    total = round(sum(categories.values()) / len(CATEGORIES))
    return ReadinessScore(total=total, categories=categories)
