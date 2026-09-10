from collections import Counter
from .config import SCENARIOS, ENGINE


class SupervisorAssistant:
    """
    Deterministic, evidence-grounded supervisor assistant.

    It never invents incidents, timestamps, locations or causes. Answers are
    computed only from the structured events produced by the vision pipeline.
    """

    def answer(self, question, incidents, meta=None):
        q = (question or "").lower().strip()
        meta = meta or {}

        if not incidents:
            return {
                "title": "No validated risk behaviour observed",
                "summary": (
                    "No behaviour passed the configured temporal and evidence "
                    "gates in this video. This does not prove that the operation "
                    "was risk-free."
                ),
                "recommendations": [],
                "evidence_count": 0,
                "findings": [],
            }

        if any(k in q for k in ("common", "frequent", "most", "top")):
            return self._top_findings(incidents)

        if any(k in q for k in ("high", "critical", "risk")):
            filtered = [
                e for e in incidents if e.get("risk") in {"HIGH", "CRITICAL"}
            ]
            return self._top_findings(
                filtered,
                title="High-risk findings",
                empty="No HIGH or CRITICAL event passed the evidence gates.",
            )

        if any(k in q for k in ("why", "classified", "reason")):
            event = max(
                incidents,
                key=lambda e: (e.get("risk_score", 0), e.get("confidence", 0)),
            )
            return {
                "title": f"Why {event.get('behaviour', 'this event')} was flagged",
                "summary": (
                    f"At {event.get('timestamp', 0):.2f}s, the system observed: "
                    f"{event.get('explanation', 'no explanation available')}. "
                    f"Risk={event.get('risk')} ({event.get('risk_score')}/100)."
                ),
                "recommendations": [event.get("recommended_action", "")],
                "evidence_count": 1,
                "findings": [{
                    "behaviour": event.get("behaviour"),
                    "timestamps_s": [event.get("timestamp")],
                    "risk": event.get("risk"),
                }],
            }

        return self._top_findings(
            incidents,
            title="Evidence-backed shift brief",
        )

    def _top_findings(self, incidents, title="Top observed findings", empty=None):
        if not incidents:
            return {
                "title": title,
                "summary": empty or "No matching evidence was found.",
                "recommendations": [],
                "evidence_count": 0,
                "findings": [],
            }

        grouped = {}
        for event in incidents:
            grouped.setdefault(event.get("behaviour", "Unknown"), []).append(event)

        ranked = sorted(
            grouped.items(),
            key=lambda item: (
                max(self._risk_rank(e.get("risk")) for e in item[1]),
                max(e.get("risk_score", 0) for e in item[1]),
                len(item[1]),
            ),
            reverse=True,
        )[:ENGINE["summary_behaviour_limit"]]

        findings = []
        recommendations = []
        for behaviour, events in ranked:
            best = max(
                events,
                key=lambda e: (e.get("risk_score", 0), e.get("confidence", 0)),
            )
            timestamps = sorted(
                {round(float(e.get("timestamp", 0)), 2) for e in events[:2]}
            )
            findings.append({
                "behaviour": behaviour,
                "risk": best.get("risk"),
                "risk_score": best.get("risk_score"),
                "timestamps_s": timestamps,
                "reason": best.get("explanation", ""),
            })
            action = best.get("recommended_action")
            if action:
                recommendations.append(action)

        summary_parts = []
        for f in findings:
            ts = ", ".join(f"{x:.2f}s" for x in f["timestamps_s"])
            summary_parts.append(
                f"{f['behaviour']} — {f['risk']} ({f['risk_score']}/100), "
                f"evidence at {ts}"
            )

        return {
            "title": title,
            "summary": " | ".join(summary_parts),
            "recommendations": recommendations,
            "evidence_count": len(incidents),
            "findings": findings,
        }

    @staticmethod
    def _risk_rank(risk):
        return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(risk, 0)
