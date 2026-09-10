# Challenge Requirements → Prototype

| Requirement in supplied brief | Implementation |
|---|---|
| Video ingestion | Local upload + OpenCV |
| Detect people/products/equipment | YOLOWorld open-vocabulary prompts |
| Object tracking | Class-aware global assignment + constant-velocity prediction |
| Behaviour identification | 10 configurable behaviour rules |
| Sequence understanding | Multi-frame temporal windows and confirmation gates |
| Risk detection | Deterministic evidence-based risk score |
| Timestamp/evidence | Source timestamp + evidence frame |
| Incident visualization | Timeline + selected-event replay + annotated video |
| AI operations assistant | Deterministic assistant grounded only in incidents |
| Daily/shift insight | Evidence-backed top findings |
| Prevention | Recommended corrective action for each event |
| Avoid repetitive output | Same track/behaviour cooldown + maximum two strongest distinct behaviours per timestamp + two key findings in summary |
| No hard-coded challenge timestamps | Decisions depend on detected tracks, motion and configured zones |
| Responsible AI | Potential risk ≠ confirmed damage; human review required |
| At least 10 scenarios | 10 challenge-aligned scenarios are implemented |
| Accuracy measurement | README documents precision/recall/F1/false-positive validation; no fabricated accuracy |
