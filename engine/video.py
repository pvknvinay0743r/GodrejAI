from __future__ import annotations
import json
import time
from pathlib import Path

import cv2
from ultralytics import YOLOWorld

from .config import (
    PRODUCT_PROMPTS,
    PERSON_NAMES,
    EQUIPMENT_NAMES,
    ENGINE,
)
from .tracker import GreedyTracker
from .detectors import BehaviourReasoner


class VideoAnalyzer:
    """
    Recorded-video analyzer.

    Pipeline:
    video -> open-vocabulary detection -> persistent tracking ->
    temporal/spatial reasoning -> conservative risk scoring -> evidence.
    """

    def __init__(
        self,
        model_path="yolov8s-worldv2.pt",
        detection_stride=1,
        imgsz=640,
        confidence=0.35,
    ):
        self.model_path = model_path
        self.detection_stride = max(1, int(detection_stride))
        self.imgsz = int(imgsz)
        self.confidence = max(0.10, min(0.90, float(confidence)))

    @staticmethod
    def _risk_rank(risk):
        return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(risk, 0)

    def analyze(
        self,
        video_path,
        output_dir="outputs",
        progress_cb=None,
        save_evidence=True,
        save_annotated_video=True,
    ):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        evidence_dir = out / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        model = YOLOWorld(self.model_path)
        model.set_classes(PRODUCT_PROMPTS)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Unable to open video: {video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if width <= 0 or height <= 0:
            cap.release()
            raise ValueError("Video has invalid dimensions.")

        tracker = GreedyTracker(
            max_distance=max(width, height) * 0.12
        )
        reasoner = BehaviourReasoner()

        incidents = []
        frame_idx = 0
        detections_run = 0
        start = time.time()
        last_event_at = {}

        annotated_path = out / "annotated_analysis.mp4"
        writer = None
        if save_annotated_video:
            writer = cv2.VideoWriter(
                str(annotated_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (width, height),
            )
            if not writer.isOpened():
                writer = None

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                frame_idx += 1
                t = (frame_idx - 1) / fps
                do_detect = frame_idx == 1 or (frame_idx - 1) % self.detection_stride == 0

                detections = []
                if do_detect:
                    results = model.predict(
                        frame,
                        imgsz=self.imgsz,
                        conf=self.confidence,
                        verbose=False,
                    )
                    for result in results:
                        if result.boxes is None:
                            continue
                        boxes = result.boxes.xyxy.cpu().tolist()
                        classes = result.boxes.cls.int().cpu().tolist()
                        confs = result.boxes.conf.cpu().tolist()
                        names = result.names

                        for box, class_id, score in zip(boxes, classes, confs):
                            label = str(names[int(class_id)]).lower()
                            score = float(score)

                            # Never let low-confidence detections enter the
                            # behaviour engine.
                            if score < self.confidence:
                                continue

                            if (
                                label in PERSON_NAMES
                                or label in EQUIPMENT_NAMES
                                or label in PRODUCT_PROMPTS
                            ):
                                detections.append(
                                    {
                                        "box": box,
                                        "label": label,
                                        "confidence": score,
                                    }
                                )
                    detections_run += 1

                tracks = tracker.update(detections, t)
                candidates = reasoner.process(tracks, width, height, t)

                # At a single timestamp, keep at most the two strongest distinct
                # behaviours. This prevents the UI from becoming repetitive while
                # retaining genuinely different high-value findings.
                candidates.sort(
                    key=lambda e: (
                        self._risk_rank(e.get("risk")),
                        e.get("risk_score", 0),
                        e.get("confidence", 0),
                    ),
                    reverse=True,
                )

                accepted = []
                seen_behaviours = set()
                for event in candidates:
                    behaviour = event["behaviour"]
                    if behaviour in seen_behaviours:
                        continue

                    signature = (
                        behaviour,
                        event.get("track_id"),
                        event.get("related_track_id"),
                    )
                    previous = last_event_at.get(signature)
                    if previous is not None and t - previous < ENGINE["event_cooldown_s"]:
                        continue

                    seen_behaviours.add(behaviour)
                    last_event_at[signature] = t

                    event["id"] = len(incidents) + 1
                    event["source_frame"] = frame_idx
                    event["analysis_latency_s"] = round(time.time() - start, 3)

                    if save_evidence:
                        safe_name = (
                            behaviour.lower()
                            .replace("/", "-")
                            .replace(" ", "_")
                            .replace("'", "")
                        )
                        evidence_path = (
                            evidence_dir
                            / f"event_{event['id']:04d}_{safe_name}_{t:07.2f}s.jpg"
                        )
                        evidence_frame = frame.copy()
                        ids = {
                            event.get("track_id"),
                            event.get("related_track_id"),
                        }
                        for track in tracks:
                            if track.track_id in ids:
                                x1, y1, x2, y2 = map(int, track.box)
                                cv2.rectangle(
                                    evidence_frame,
                                    (x1, y1),
                                    (x2, y2),
                                    (0, 220, 170),
                                    2,
                                )
                                cv2.putText(
                                    evidence_frame,
                                    f"ID {track.track_id} {track.label}",
                                    (x1, max(18, y1 - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.55,
                                    (0, 220, 170),
                                    2,
                                )
                        cv2.putText(
                            evidence_frame,
                            f"{behaviour} | {event['risk']} {event['risk_score']}/100 | {t:.2f}s",
                            (20, 32),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.62,
                            (30, 240, 210),
                            2,
                        )
                        cv2.imwrite(str(evidence_path), evidence_frame)
                        event["evidence_frame"] = str(evidence_path)

                    incidents.append(event)
                    accepted.append(event)

                    if len(accepted) >= ENGINE["summary_behaviour_limit"]:
                        break

                if writer:
                    self._draw_frame(frame, tracks, accepted)
                    writer.write(frame)

                if progress_cb and total:
                    progress_cb(min(1.0, frame_idx / total))

        finally:
            cap.release()
            if writer:
                writer.release()

        duration = total / fps if total else frame_idx / fps
        processing = time.time() - start

        key_findings = self._build_key_findings(incidents)

        meta = {
            "fps": fps,
            "frames": total or frame_idx,
            "width": width,
            "height": height,
            "duration_s": round(duration, 2),
            "detections_run": detections_run,
            "detection_stride": self.detection_stride,
            "processing_s": round(processing, 2),
            "realtime_factor": round(duration / max(0.001, processing), 2),
            "tracking": tracker.stats(),
            "engine": (
                "YOLOWorld perception + class-aware global assignment tracking + "
                "temporal/spatial behaviour reasoning + conservative evidence gates"
            ),
            "model": self.model_path,
            "model_confidence": self.confidence,
            "annotated_video": str(annotated_path) if writer else None,
            "key_findings": key_findings,
            "accuracy_note": (
                "Behaviour confidence is evidence confidence, not a validated accuracy "
                "percentage. Precision/recall must be measured on labelled warehouse footage."
            ),
        }

        result = {
            "video": str(video_path),
            "meta": meta,
            "incidents": incidents,
            "scenario_coverage": sorted({x["behaviour"] for x in incidents}),
            "key_findings": key_findings,
        }
        (out / "analysis.json").write_text(
            json.dumps(result, indent=2),
            encoding="utf-8",
        )
        return incidents, meta

    @staticmethod
    def _build_key_findings(incidents):
        """
        Return at most two data-backed behaviour findings. Each behaviour appears
        once and contains up to two representative timestamps, preventing repetitive
        output while retaining evidence for genuinely distinct behaviours.
        """
        grouped = {}
        for event in incidents:
            name = event.get("behaviour", "Unknown")
            grouped.setdefault(name, []).append(event)

        ranked = sorted(
            grouped.items(),
            key=lambda item: (
                max(VideoAnalyzer._risk_rank(e.get("risk")) for e in item[1]),
                max(e.get("risk_score", 0) for e in item[1]),
                len(item[1]),
            ),
            reverse=True,
        )[:ENGINE["summary_behaviour_limit"]]

        findings = []
        for behaviour, events in ranked:
            events = sorted(events, key=lambda e: e.get("risk_score", 0), reverse=True)
            representative = sorted(
                {round(float(e.get("timestamp", 0)), 2) for e in events[:2]}
            )
            best = events[0]
            findings.append(
                {
                    "behaviour": behaviour,
                    "risk": best.get("risk"),
                    "risk_score": best.get("risk_score"),
                    "timestamps_s": representative,
                    "reason": best.get("explanation"),
                }
            )
        return findings

    @staticmethod
    def _draw_frame(frame, tracks, events):
        for track in tracks:
            x1, y1, x2, y2 = map(int, track.box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (66, 214, 168), 1)
            cv2.putText(
                frame,
                f"ID {track.track_id} {track.label}",
                (x1, max(16, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (66, 214, 168),
                1,
            )

        y = 28
        for event in events[:2]:
            text = (
                f"{event['risk']} {event['risk_score']}: "
                f"{event['behaviour']} · {event['timestamp']:.2f}s"
            )
            cv2.putText(
                frame,
                text,
                (18, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (30, 240, 210),
                2,
            )
            y += 22
