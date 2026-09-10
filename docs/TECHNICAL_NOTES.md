# Technical Notes

## Perception

Ultralytics YOLOWorld is used with a curated warehouse vocabulary. The engine does not treat arbitrary detector output as a product.

Default precision-first profile:
- confidence: 0.35
- inference size: 640
- detection interval: every frame

These values are configurable in the UI.

## Tracking

Tracks are class-aware and assigned globally with IoU and predicted centre distance. A constant-velocity prediction bridges short detector gaps.

Track history contains:
- timestamp
- centre
- width/height
- area
- velocity
- speed
- acceleration
- detection/prediction state
- confidence

## Temporal reasoning

Continuous behaviours require repeated supporting observations. This is important because a single noisy bounding box or frame should not become an incident.

Drop/impact is treated differently: it requires a rapid downward phase followed by impact-like deceleration within a short temporal window.

## Duplicate suppression

There are two layers:
1. behaviour/track cooldown inside the reasoner;
2. accepted-event cooldown in the video analyzer.

The summary then groups events by behaviour and surfaces at most two strongest distinct findings.

## Risk

Risk is deterministic and uses:
- base behaviour severity
- detector confidence
- evidence quality
- persistence
- impact proxy

Recurrence is intentionally not used to inflate severity.

## Evidence contract

Each event contains:
- behaviour
- risk
- risk score
- timestamp
- track ID
- related track ID when relevant
- observed evidence
- explanation
- recommended action
- risk rationale
- status
- damage_confirmed=False

This keeps the distinction:

**Observed behaviour → Potential risk → Human review**

rather than:

**Video → confirmed damage**

## Production path

For a production-grade system, replace/augment heuristic temporal rules with a warehouse-specific temporal action-recognition model trained and validated on labelled clips. Add product metadata for weight/fragility and calibrated camera zones for precise spatial rules.
