from __future__ import annotations

from .models import CATEGORIES, SEVERITY_WEIGHTS, Finding, ReadinessScore


RESIDUAL_REMEDIATION_WEIGHTS = {
    "high": 4,
    "medium": 3,
    "low": 2,
    "manual": 35,
}

PENDING_BENCHMARK_CAPS = {
    "benchmark": 85,
    "deployment": 95,
}


def calculate_score(
    findings: list[Finding],
    after_patch: bool = False,
    benchmark_verified: bool = True,
) -> ReadinessScore:
    categories: dict[str, int] = {}
    for category in CATEGORIES:
        penalty = 0
        for finding in findings:
            if finding.category != category:
                continue
            if after_patch and finding.remediable:
                penalty += RESIDUAL_REMEDIATION_WEIGHTS.get(finding.severity, 2)
            else:
                penalty += SEVERITY_WEIGHTS.get(finding.severity, 10)
        categories[category] = max(0, 100 - penalty)

    if after_patch and not benchmark_verified:
        for category, cap in PENDING_BENCHMARK_CAPS.items():
            categories[category] = min(categories[category], cap)

    total = round(sum(categories.values()) / len(CATEGORIES))
    return ReadinessScore(total=total, categories=categories)
