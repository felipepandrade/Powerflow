"""Objetos de valor para resultados analíticos honestos."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from taskflow.domain.metrics.registry import MetricDefinition

MetricState = Literal["known", "unknown", "suppressed"]


@dataclass(frozen=True)
class MetricResult:
    """Envelope RF-I.6 independente de banco e framework."""
    definition: MetricDefinition
    period_start: date
    period_end: date
    value: float | None
    numerator: float | None
    denominator: float | None
    sample_size: int
    coverage_pct: float | None
    coverage_level: str
    state: MetricState
    caveat: str
    is_suppressed: bool = False
    suppression_reason: str | None = None
    dimension_key: str = "_total"
    dimension_value: str | None = None
    period_comparison: dict[str, float | None] | None = None
    provenance_ids: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.definition.id,
            "metric_version": self.definition.version,
            "value": self.value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "sample_size": self.sample_size,
            "coverage": {"pct": self.coverage_pct, "level": self.coverage_level},
            "coverage_pct": self.coverage_pct,
            "coverage_level": self.coverage_level,
            "state": self.state,
            "is_suppressed": self.is_suppressed,
            "suppression_reason": self.suppression_reason,
            "caveat": self.caveat,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "period_comparison": self.period_comparison,
            "dimension_key": self.dimension_key,
            "dimension_value": self.dimension_value,
            "formula": self.definition.formula,
            "provenance": {
                "source": self.definition.source,
                "data_origin": self.definition.data_origin,
                "coverage_basis": self.definition.coverage_basis,
                "record_ids": list(self.provenance_ids),
            },
        }
