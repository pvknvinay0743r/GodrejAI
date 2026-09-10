# Validation Kit — Godrej Warehouse AI

This folder is deliberately **ground-truth driven**. It does not infer accuracy from filenames, timestamps, alert counts, or detector confidence.

## 1. Create labels

Copy `ground_truth_template.csv` to a new CSV and add one row per manually verified behaviour interval:

```csv
video,behaviour,start_s,end_s
my_video.mp4,Dropping / impact,12.0,13.2
my_video.mp4,Dragging,20.5,25.0
```

For normal/no-event footage, do not add a behaviour row. The validator treats unlabelled time as negative for the listed target behaviours.

## 2. Generate predictions

Run the analyzer once per video. It writes `outputs/analysis.json`.

```bash
python evaluate_video.py path/to/video.mp4 --output-dir outputs/my_video
```

Then validate against your labelled CSV:

```bash
python validation/validate_predictions.py \
  --analysis outputs/my_video/analysis.json \
  --ground-truth validation/my_labels.csv \
  --video my_video.mp4
```

For multiple videos, run the validator once per analysis file or combine exported prediction JSON files in your own evaluation pipeline.

## 3. Metrics

The validator reports, per behaviour and overall:

- TP / FP / FN
- precision
- recall
- F1
- false-positive rate
- average detection latency when a prediction overlaps a ground-truth interval

An event is considered a true positive when its timestamp falls inside a labelled interval for the same behaviour. This interval-overlap rule is intentionally simple and transparent for a hackathon validation set; it is not a substitute for frame-level action-recognition benchmarking.

## 4. Accuracy claims

Never call `confidence` an accuracy percentage. Never claim 95%/99% accuracy unless the number comes from this or another documented labelled evaluation protocol.

Tune thresholds on a development set and report final metrics on a held-out test set. Keep the test labels hidden while tuning.
