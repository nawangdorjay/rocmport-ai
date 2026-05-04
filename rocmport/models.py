from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


CATEGORIES = ["code", "environment", "serving", "benchmark", "deployment"]

CATEGORY_LABELS = {
    "code": "Code portability",
    "environment": "Environment readiness",
    "serving": "Serving readiness",
    "benchmark": "Benchmark readiness",
    "deployment": "Deployment readiness",
}

SEVERITY_WEIGHTS = {
    "high": 35,
    "medium": 22,
    "low": 10,
    "manual": 35,
}


@dataclass(frozen=True)
class Finding:
    id: str
    category: str
    severity: str
    path: str
    line: int
    message: str
    suggested_fix: str
    remediable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessScore:
    total: int
    categories: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {"total": self.total, "categories": self.categories}


@dataclass
class MigrationBundle:
    repo_name: str
    findings: list[Finding]
    before_score: ReadinessScore
    after_score: ReadinessScore
    patch_diff: str
    dockerfile: str
    runbook: str
    report: str
    benchmark: dict[str, Any]
    cookbook: str
    feedback: str
    artifact_paths: dict[str, str] = field(default_factory=dict)

    def findings_table(self) -> list[list[Any]]:
        return [
            [
                finding.severity,
                CATEGORY_LABELS.get(finding.category, finding.category),
                finding.path,
                finding.line,
                finding.message,
                finding.suggested_fix,
            ]
            for finding in self.findings
        ]
