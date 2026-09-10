from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def load_truth(path: Path, video_name: str):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("video") or row["video"].startswith("#"):
                continue
            if Path(row["video"]).name != Path(video_name).name:
                continue
            rows.append({
                "behaviour": row["behaviour"].strip(),
                "start": float(row["start_s"]),
                "end": float(row["end_s"]),
            })
    return rows


def main():
    p = argparse.ArgumentParser(description="Validate behaviour events against manually labelled intervals.")
    p.add_argument("--analysis", required=True)
    p.add_argument("--ground-truth", required=True)
    p.add_argument("--video", required=True)
    args = p.parse_args()

    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    predictions = analysis.get("incidents", [])
    truth = load_truth(Path(args.ground_truth), args.video)

    behaviours = sorted({x["behaviour"] for x in truth} | {x.get("behaviour") for x in predictions if x.get("behaviour")})
    matched_truth = set()
    per = {}

    for behaviour in behaviours:
        gt = [x for i, x in enumerate(truth) if x["behaviour"] == behaviour]
        pred = [x for x in predictions if x.get("behaviour") == behaviour]
        tp = 0
        fp = 0
        latencies = []
        for event in pred:
            ts = float(event.get("timestamp", 0))
            match = next(
                (i for i, interval in enumerate(gt)
                 if i not in matched_truth and interval["start"] <= ts <= interval["end"]),
                None,
            )
            if match is None:
                fp += 1
            else:
                tp += 1
                matched_truth.add(match)
                latencies.append(max(0.0, ts - gt[match]["start"]))
        fn = len(gt) - sum(1 for i in range(len(gt)) if i in matched_truth)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        # Event-level FPR requires a defined negative opportunity. We use the
        # number of predictions outside labelled intervals over all predictions
        # plus the number of labelled-negative windows represented by the video.
        duration = float(analysis.get("meta", {}).get("duration_s", 0.0))
        positive_time = sum(max(0.0, x["end"] - x["start"]) for x in gt)
        negative_time = max(0.0, duration - positive_time)
        fp_rate = fp / max(1.0, fp + negative_time)
        per[behaviour] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_positive_rate_proxy": round(fp_rate, 6),
            "average_detection_latency_s": round(sum(latencies) / len(latencies), 3) if latencies else None,
        }

    total_tp = sum(x["tp"] for x in per.values())
    total_fp = sum(x["fp"] for x in per.values())
    total_fn = sum(x["fn"] for x in per.values())
    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    result = {
        "video": args.video,
        "ground_truth": str(args.ground_truth),
        "prediction_source": str(args.analysis),
        "overall": {
            "tp": total_tp, "fp": total_fp, "fn": total_fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "per_behaviour": per,
        "method_note": "Event timestamp must fall inside a manually labelled interval for the same behaviour. Confidence is not treated as accuracy.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
