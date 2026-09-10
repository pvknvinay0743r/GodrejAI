# Godrej Warehouse AI — Video Intelligence

## 1. Purpose

This prototype implements the challenge flow:

**Video → AI perception → persistent tracking → temporal behaviour reasoning → risk detection → evidence → supervisor intervention → prevention**

The challenge asks for an AI field-intelligence assistant that understands warehouse loading/unloading behaviour, identifies actions that could cause product damage, and helps people intervene early. The prototype therefore reports **potential risk**, not confirmed damage.

## 2. What is improved in this build

### Accuracy-first behaviour detection
- Detection confidence defaults to **0.35**.
- Inference size defaults to **640**.
- Detection runs on **every frame by default** for better temporal resolution.
- Continuous behaviours require multiple supporting observations.
- Drop/impact requires both a rapid downward phase and impact-like deceleration.
- Low-confidence/unknown classes are not silently treated as products.
- Predicted tracker positions reduce continuity gaps but evidence quality is lowered when detections are missing.
- Repeated behaviour on the same track is suppressed during a configurable cooldown.
- At one timestamp, at most **two strongest distinct behaviours** are surfaced.

### Better tracking
- Class-aware global assignment using IoU + predicted centre distance.
- Constant-velocity prediction between detector frames.
- Track history stores position, velocity, acceleration, geometry, confidence and prediction state.
- Track identity is retained through short detector gaps.

### Evidence-grounded answers
The supervisor assistant is deterministic. It reads only the structured incidents produced by the vision engine. It does not invent timestamps, behaviours, locations or confirmed damage.

### Better UX
- Clear product-style folder/project name.
- Reset clears the current analysis, generated evidence and uploader state.
- Streamlit deployment/menu chrome is hidden.
- One-click Windows/Linux launchers check dependencies instead of reinstalling them every run.
- Dashboard surfaces up to two key findings instead of repeating the same behaviour/count everywhere.

## 3. Challenge alignment

The supplied challenge document calls for:
- video ingestion
- object detection/tracking
- behaviour identification
- sequence/temporal reasoning
- risk classification
- timestamped evidence
- AI explanation/recommendation
- prevention framing
- at least 10 predefined behaviours/scenarios
- dashboard/incident replay
- responsible AI and human review

This build provides those capabilities within a controlled-video prototype.

The challenge document specifically emphasizes combining **Object Detection + Object Tracking + Action Recognition + Temporal Reasoning + Risk Classification** and understanding action sequences rather than individual frames. This implementation provides temporal reasoning and risk classification; it does **not** pretend that generic RGB detection alone is a production-grade action-recognition model.

## 4. Behaviour taxonomy

The engine supports 10 challenge-aligned scenarios:

1. Dropping / impact
2. Dragging
3. Rough handling
4. Incorrect stacking
5. Unstable stacking
6. Outside designated area
7. Unsafe loading sequence
8. Unsafe person-product interaction
9. Product orientation change
10. Rolling / uncontrolled movement

Only behaviours whose evidence gates are satisfied are reported. The system does not manufacture a result just to fill all categories.

## 5. Run on Windows

Double-click:

`run.bat`

The launcher:
1. creates `.venv` if needed;
2. checks whether the required packages are already installed;
3. installs dependencies only when missing;
4. starts the local application.

There is no separate Streamlit installation command to run manually.

The first successful AI run may download/cache the configured YOLOWorld model.

## 6. Outputs

`outputs/`
- `analysis.json` — machine-readable audit
- `annotated_analysis.mp4` — replay with tracks/events
- `evidence/` — timestamped evidence frames

The output is generated from the uploaded video; filenames and fixed timestamps are not used to decide behaviour.

## 7. Accuracy methodology

Do not present the prototype's `confidence` or `risk_score` as model accuracy.

For a serious competition claim, create a labelled validation set containing:
- normal handling
- each target behaviour
- different camera angles
- different lighting
- occlusion
- different product sizes
- empty/no-event footage

Then report:
- precision
- recall
- F1
- false-positive rate
- detection latency
- per-behaviour confusion matrix

The challenge itself recommends behaviour accuracy, precision/recall, false-positive rate and detection latency as useful AI performance metrics.

## 8. Important visual limitations

The engine deliberately avoids unsupported claims.

For example, ordinary RGB footage cannot reliably establish:
- actual product weight
- product fragility
- confirmed physical damage
- floor wetness
- exact force in Newtons

Therefore the system uses visual geometry and motion as **proxies** and labels results as potential risk.

## 9. Configuration

Behaviour and tracking thresholds live in:

`engine/config.py`

They can also be overridden with environment variables beginning with `GODREJ_`.

The most useful controls are:
- `GODREJ_MIN_DETECTION_CONF`
- `GODREJ_CONFIRM_FRAMES`
- `GODREJ_EVENT_COOLDOWN`
- `GODREJ_DRAG_SPEED`
- `GODREJ_DROP_VERTICAL_SPEED`
- `GODREJ_DROP_SPEED`
- `GODREJ_IMPACT_DECELERATION`
- `GODREJ_ROUGH_SPEED_CHANGE`

Do not tune these on the same footage used to claim final accuracy.

## 10. Tests

Run:

```text
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover risk bounds, taxonomy size and tracker identity/class separation.

## 11. Competition positioning

The supplied judging criteria weight:
- Innovation & Creativity — 15%
- Technical Execution — 20%
- AI + Video Intelligence Integration — 20%
- User Experience & User Feedback — 10%
- Damage Prevention & Business Impact — 20%
- Presentation Quality — 15%

For a top-tier submission, the demo should therefore show a complete prevention loop:

**Observed behaviour → evidence → risk → intervention → prevention**

Do not claim “25 damaged products detected” from video alone. The challenge explicitly encourages framing the result as high-risk handling events identified early so corrective intervention can occur before damage.

## 12. Demo sequence

Use a short, controlled video containing clearly staged scenarios.

Recommended demo:
1. normal handling — show no alert;
2. controlled dragging — show timestamp/evidence;
3. controlled drop/impact — show timestamp/evidence;
4. show the assistant explaining why the event was flagged;
5. show the annotated replay;
6. show the audit JSON;
7. finish with prevention and human-review messaging.

The prototype should be evaluated on labelled evidence rather than on how many alerts it produces.


## 13. Top-3 strategy

See `docs/TOP3_STRATEGY.md` for the judge narrative, validation plan and demo sequence designed around the supplied judging weights.
