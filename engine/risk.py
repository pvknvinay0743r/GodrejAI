from dataclasses import dataclass
from .config import RISK_ORDER

@dataclass
class RiskResult:
    risk: str
    score: int
    rationale: str

def classify(
    base_risk: str,
    confidence: float,
    persistence_s: float = 0.0,
    impact: float = 0.0,
    evidence_quality: float = 1.0,
) -> RiskResult:
    """
    Deterministic risk score.

    Important: recurrence is not allowed to inflate severity. Repeated observations
    are consolidated separately so the same incident cannot become "critical" merely
    because it was seen many times.
    """
    base = RISK_ORDER.get(base_risk, 2)
    c = max(0.0, min(1.0, confidence))
    q = max(0.0, min(1.0, evidence_quality))
    imp = max(0.0, min(1.0, impact))
    persistence = max(0.0, min(1.0, persistence_s / 3.0))

    # Evidence quality is deliberately more influential than raw detector confidence.
    score = int(
        base * 15
        + c * 30
        + q * 25
        + persistence * 10
        + imp * 20
    )
    score = max(0, min(100, score))

    # A high base severity still requires reasonable evidence.
    if q < 0.45 or c < 0.40:
        risk = "MEDIUM"
    elif score >= 82 and base >= 4:
        risk = "CRITICAL"
    elif score >= 62 and base >= 3:
        risk = "HIGH"
    elif score >= 38:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    rationale = (
        f"Base={base_risk}; detection confidence={c:.0%}; "
        f"evidence quality={q:.0%}; persistence={persistence_s:.1f}s; "
        f"impact proxy={imp:.0%}; score={score}/100."
    )
    return RiskResult(risk, score, rationale)
