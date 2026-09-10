# Submission Checklist

## Prototype
- [ ] Upload a representative warehouse video
- [ ] Demonstrate at least 3–5 scenarios in the demo video
- [ ] Show persistent object IDs
- [ ] Show behaviour timestamps
- [ ] Show evidence frames
- [ ] Show risk classification
- [ ] Show corrective recommendation
- [ ] Show annotated replay
- [ ] Show supervisor assistant
- [ ] Show audit JSON

## Accuracy
- [ ] Label validation footage
- [ ] Measure precision/recall/F1
- [ ] Measure false-positive rate
- [ ] Measure detection latency
- [ ] Review false positives manually
- [ ] Do not report unvalidated percentages

## Responsible AI
- [ ] Obtain permission for employee footage
- [ ] Minimize stored video
- [ ] Restrict access to incident evidence
- [ ] Require human review for significant incidents
- [ ] Do not use the system for automated punitive decisions
- [ ] Do not claim physical damage without independent evidence

## Demo story

**Normal operation → risky behaviour → timestamped evidence → explanation → intervention → prevention**

Keep the story focused on business impact rather than simply showing model detections.

## Final integrity checks

Before submission:

- [ ] Run `python -m unittest discover -s tests -v` and keep the output as validation evidence.
- [ ] Run `python tools/audit_project.py .`; it must pass.
- [ ] Validate target behaviours on a manually labelled development/test set using `validation/validate_predictions.py`.
- [ ] Do not report detector confidence as accuracy.
- [ ] Do not report business savings or prevented damage unless independently measured.
- [ ] Demonstrate at least 3–5 representative scenarios in the demo, while the prototype taxonomy contains at least 10 scenarios as required by the brief.
- [ ] Show at least one normal-handling segment with no alert.
- [ ] Explain that weight, fragility, physical damage and other non-visual facts are not asserted from generic RGB video alone.
- [ ] Keep significant incidents subject to human review.
