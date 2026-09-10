from __future__ import annotations

from types import SimpleNamespace
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.detectors import BehaviourReasoner


def track(track_id, label, boxes):
    history = []
    for i, box in enumerate(boxes):
        cx = (box[0] + box[2]) / 2
        cy = (box[1] + box[3]) / 2
        history.append({
            "t": i * 0.1, "cx": cx, "cy": cy,
            "w": box[2] - box[0], "h": box[3] - box[1],
            "area": (box[2] - box[0]) * (box[3] - box[1]),
            "bottom": box[3], "conf": 0.9, "predicted": False,
            "vx": 0.0, "vy": 0.0, "speed": 0.0, "acceleration": 0.0,
        })
    for i in range(1, len(history)):
        dt = history[i]["t"] - history[i-1]["t"]
        history[i]["vx"] = (history[i]["cx"] - history[i-1]["cx"]) / dt
        history[i]["vy"] = (history[i]["cy"] - history[i-1]["cy"]) / dt
        history[i]["speed"] = (history[i]["vx"] ** 2 + history[i]["vy"] ** 2) ** 0.5
    return SimpleNamespace(
        track_id=track_id, label=label, confidence=0.9,
        box=tuple(boxes[-1]), history=history, hits=len(boxes),
        center=((boxes[-1][0] + boxes[-1][2]) / 2, (boxes[-1][1] + boxes[-1][3]) / 2),
        width=boxes[-1][2] - boxes[-1][0], height=boxes[-1][3] - boxes[-1][1],
        bottom=boxes[-1][3], last_time=history[-1]["t"],
    )


if __name__ == "__main__":
    # This is a structural smoke test, not an accuracy claim.
    reasoner = BehaviourReasoner()
    normal = track(1, "carton", [[400, 400, 500, 500]] * 4)
    events = reasoner.process([normal], 1280, 720, 0.3)
    assert not events, f"Normal stationary carton produced events: {events}"
    print("PASS: normal stationary input produces no behaviour event.")
