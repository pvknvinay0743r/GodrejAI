# Top-3 Competition Strategy

The supplied brief weights **Technical Execution (20%)**, **AI + Video Intelligence Integration (20%)**, and **Damage Prevention & Business Impact (20%)** heavily. The strongest path is therefore a measurable prevention workflow rather than a dashboard full of alerts.

## 1. Win on technical credibility

Show the full chain:

**Detection → Tracking → Temporal reasoning → Risk → Evidence → Intervention**

Explain one incident frame-by-frame. The important differentiator is sequence understanding, not simply detecting a person and a box.

## 2. Win on accuracy

Use a controlled validation set.

Report:
- precision
- recall
- F1
- false-positive rate
- detection latency

Show at least one example where the system deliberately produces **no alert** for normal handling.

A conservative detector that explains its evidence is more credible than a detector that produces many unsupported alerts.

## 3. Win on business impact

Translate events into prevention:

**Risky handling observed → supervisor notified → intervention → potential damage avoided**

Do not claim money saved or damage prevented unless those numbers are measured.

## 4. Win on UX

The dashboard intentionally surfaces:
- the strongest two distinct findings
- timestamps
- risk
- evidence
- corrective action

Repeated alerts are consolidated so the judge can understand the result quickly.

## 5. Win on responsible AI

Explicitly say:
- this is process-improvement intelligence;
- it is not an automated employee punishment system;
- significant incidents require human review;
- video alone cannot prove physical product damage;
- physical weight/fragility should come from metadata or validated sensors/models.

## 6. 90-second demo narrative

1. Upload controlled warehouse video.
2. Show object IDs persist through motion.
3. Show a normal segment with no alert.
4. Trigger a clearly staged risky behaviour.
5. Jump to its timestamp.
6. Show evidence and the reason.
7. Ask the supervisor assistant for the top findings.
8. Show corrective action.
9. Show annotated replay and audit JSON.
10. End with the prevention metric/validation result.

## 7. What not to do

Avoid:
- fake accuracy percentages;
- hard-coded timestamps;
- alerts generated only from filenames;
- calling visual size “weight”;
- claiming a product is damaged without evidence;
- showing 20 repetitive cards for one incident;
- relying on an LLM to invent an explanation;
- presenting Streamlit/developer controls as part of the product.

## 8. The strongest differentiator

The core message should be:

> **We are not building another CCTV viewer. We are converting video into evidence-backed intervention signals before damage occurs.**

That statement is supported by the architecture: persistent tracking, temporal reasoning, risk classification, timestamped evidence and prevention-oriented recommendations.
