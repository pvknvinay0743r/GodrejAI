from __future__ import annotations
from collections import defaultdict, deque
import math

from .config import PERSON_NAMES, EQUIPMENT_NAMES, DEFAULT_ZONES, SCENARIOS, MOTION, ENGINE
from .risk import classify


class BehaviourReasoner:
    """
    Conservative temporal/spatial behaviour engine.

    A candidate must be supported by several consecutive observations for
    continuous behaviours. One-frame noise is therefore not immediately shown
    as an incident. Pulse events such as a drop still require a strong motion
    pattern and an impact-like deceleration.
    """

    CONTINUOUS = {
        "Dragging",
        "Rough handling",
        "Incorrect stacking",
        "Unstable stacking",
        "Outside designated area",
        "Unsafe loading sequence",
        "Unsafe person-product interaction",
        "Product orientation change",
        "Rolling / uncontrolled movement",
    }

    def __init__(self):
        self.last_emit = {}
        self.confirmations = defaultdict(int)
        self.recurrence = defaultdict(int)
        self.orientation_baseline = {}
        self.recent_drop_peak = {}
        self.loading_entry_time = {}
        self.cooldown = ENGINE["event_cooldown_s"]

    @staticmethod
    def _is_person(t):
        return t.label.lower() in PERSON_NAMES

    @staticmethod
    def _is_equipment(t):
        return t.label.lower() in EQUIPMENT_NAMES

    @staticmethod
    def _is_product(t):
        # Never treat an unknown class as a product. This prevents random
        # detections from becoming warehouse incidents.
        return not BehaviourReasoner._is_person(t) and not BehaviourReasoner._is_equipment(t)

    @staticmethod
    def _near(a, b, scale=0.45):
        ax, ay = a.center
        bx, by = b.center
        return math.hypot(ax - bx, ay - by) <= scale * max(
            a.width, a.height, b.width, b.height
        )

    @staticmethod
    def _overlap(a, b):
        x = max(0, min(a.box[2], b.box[2]) - max(a.box[0], b.box[0]))
        return x / max(1, min(a.width, b.width))

    @staticmethod
    def _inside(box, zone, width, height):
        cx = (box[0] + box[2]) / 2
        cy = (box[1] + box[3]) / 2
        return (
            zone.x1 * width <= cx <= zone.x2 * width
            and zone.y1 * height <= cy <= zone.y2 * height
        )

    @staticmethod
    def _actual_ratio(track):
        if not track.history:
            return 0.0
        return sum(1 for x in track.history[-8:] if not x.get("predicted")) / min(8, len(track.history))

    def _candidate(self, key, strong=False):
        if strong:
            self.confirmations[key] = ENGINE["continuous_confirmation_frames"]
            return True
        self.confirmations[key] += 1
        # Do not keep counters alive forever when a candidate disappears.
        return self.confirmations[key] >= ENGINE["continuous_confirmation_frames"]

    def _clear_missing(self, active_keys):
        for key in list(self.confirmations):
            if key not in active_keys:
                self.confirmations[key] = max(0, self.confirmations[key] - 1)
                if self.confirmations[key] == 0:
                    del self.confirmations[key]

    def _emit(self, events, name, t, track_id, conf, impact, evidence,
              related_track_id=None, strong=False):
        key = (name, track_id, related_track_id)
        if name in self.CONTINUOUS and not self._candidate(key, strong=strong):
            return

        previous = self.last_emit.get(key)
        if previous is not None and t - previous < self.cooldown:
            return

        self.last_emit[key] = t
        self.recurrence[key] += 1

        desc, base, action = SCENARIOS[name]
        persistence = float(evidence.get("persistence_s", 0.0))
        quality = float(evidence.get("evidence_quality", 0.0))
        rr = classify(base, conf, persistence, impact, quality)

        event = {
            "id": None,
            "behaviour": name,
            "risk": rr.risk,
            "risk_score": rr.score,
            "confidence": round(max(0.0, min(1.0, conf)), 3),
            "timestamp": round(t, 2),
            "track_id": track_id,
            "related_track_id": related_track_id,
            "subject": evidence.get("subject", "product"),
            "evidence": evidence,
            "explanation": evidence.get("explanation", desc),
            "why_risky": (
                "Observed evidence is consistent with this behaviour. "
                "It represents potential operational risk, not confirmed product damage."
            ),
            "recommended_action": action,
            "risk_rationale": rr.rationale,
            "status": "POTENTIAL_RISK",
            "damage_confirmed": False,
            "detection_source": "TEMPORAL_BEHAVIOUR_ENGINE",
        }
        events.append(event)

    def process(self, tracks, width, height, t):
        products = [x for x in tracks if self._is_product(x) and x.hits >= ENGINE["minimum_track_hits"]]
        people = [x for x in tracks if self._is_person(x) and x.hits >= 2]
        events = []
        active_keys = set()

        designated = DEFAULT_ZONES["designated_zone"]
        loading = DEFAULT_ZONES["loading_zone"]

        for p in products:
            if len(p.history) < 4:
                continue

            h = p.history
            cur = h[-1]
            old = h[-4]
            dt = max(0.05, cur["t"] - old["t"])
            vx = (cur["cx"] - old["cx"]) / dt
            vy = (cur["cy"] - old["cy"]) / dt
            speed = math.hypot(vx, vy)
            actual_ratio = self._actual_ratio(p)

            # A sustained motion window is much more reliable than a single
            # frame's velocity.
            recent = h[-5:]
            recent_speeds = [x.get("speed", 0.0) for x in recent]
            moving_frames = sum(s > 35 for s in recent_speeds)
            horizontal_frames = sum(
                abs(x.get("vx", 0.0)) > MOTION["drag_horizontal_px_s"]
                and abs(x.get("vy", 0.0)) < abs(x.get("vx", 0.0)) * 0.65
                for x in recent
            )

            near_person = any(self._near(p, w, 0.50) for w in people)
            floor = p.bottom / max(1, height)

            # Dragging: sustained horizontal floor-level movement + person proximity.
            key = ("Dragging", p.track_id, None)
            if (
                near_person
                and floor > 0.55
                and horizontal_frames >= 3
                and moving_frames >= 3
            ):
                active_keys.add(key)
                self._emit(
                    events, "Dragging", t, p.track_id,
                    min(0.96, p.confidence * 0.70 + actual_ratio * 0.30),
                    min(1.0, speed / 220.0),
                    {
                        "speed_px_s": round(speed, 1),
                        "horizontal_velocity_px_s": round(vx, 1),
                        "vertical_velocity_px_s": round(vy, 1),
                        "person_nearby": True,
                        "persistence_s": round(dt, 2),
                        "evidence_quality": round(actual_ratio, 3),
                        "subject": p.label,
                    },
                )

            # Rolling: sustained horizontal movement + changing box geometry.
            width_change = abs(p.width - h[-3]["w"]) / max(1, h[-3]["w"])
            key = ("Rolling / uncontrolled movement", p.track_id, None)
            if (
                abs(vx) > MOTION["roll_horizontal_px_s"]
                and abs(vy) < abs(vx) * 0.60
                and width_change > 0.16
                and moving_frames >= 3
            ):
                active_keys.add(key)
                self._emit(
                    events, "Rolling / uncontrolled movement", t, p.track_id,
                    min(0.93, p.confidence * 0.70 + actual_ratio * 0.30),
                    min(1.0, abs(vx) / 240.0),
                    {
                        "horizontal_velocity_px_s": round(vx, 1),
                        "bbox_width_change": round(width_change, 3),
                        "persistence_s": round(dt, 2),
                        "evidence_quality": round(actual_ratio, 3),
                        "subject": p.label,
                    },
                )

            # Drop/impact: require a downward high-speed phase AND an impact-like
            # deceleration. This avoids flagging normal downward movement.
            previous_speed = h[-2].get("speed", 0.0)
            downward_phase = vy > MOTION["drop_vertical_px_s"] and speed > MOTION["drop_speed_px_s"]
            deceleration = previous_speed - speed
            impact_phase = deceleration > MOTION["impact_deceleration"] and previous_speed > MOTION["drop_speed_px_s"]
            if downward_phase:
                self.recent_drop_peak[p.track_id] = {
                    "t": t,
                    "vy": vy,
                    "speed": speed,
                    "y": p.center[1],
                }

            peak = self.recent_drop_peak.get(p.track_id)
            if peak and impact_phase and t - peak["t"] <= 1.0:
                self._emit(
                    events, "Dropping / impact", t, p.track_id,
                    min(0.98, p.confidence * 0.65 + actual_ratio * 0.35),
                    min(1.0, max(0.0, deceleration) / 420.0),
                    {
                        "peak_downward_velocity_px_s": round(peak["vy"], 1),
                        "pre_impact_speed_px_s": round(previous_speed, 1),
                        "post_impact_speed_px_s": round(speed, 1),
                        "deceleration_px_s2": round(deceleration, 1),
                        "impact_delay_s": round(t - peak["t"], 2),
                        "evidence_quality": round(actual_ratio, 3),
                        "subject": p.label,
                        "explanation": (
                            f"Track {p.track_id} showed a rapid downward motion "
                            "followed by a strong deceleration consistent with an impact."
                        ),
                        "persistence_s": round(t - peak["t"], 2),
                    },
                    strong=True,
                )
                self.recent_drop_peak.pop(p.track_id, None)

            # Rough handling: acceleration must be high AND speed must remain meaningful.
            acc = abs(cur.get("acceleration", 0.0))
            key = ("Rough handling", p.track_id, None)
            if acc > MOTION["rough_speed_change"] and speed > MOTION["rough_speed"]:
                active_keys.add(key)
                self._emit(
                    events, "Rough handling", t, p.track_id,
                    min(0.94, p.confidence * 0.65 + actual_ratio * 0.35),
                    min(1.0, acc / 400.0),
                    {
                        "speed_px_s": round(speed, 1),
                        "acceleration_px_s2": round(acc, 1),
                        "persistence_s": round(dt, 2),
                        "evidence_quality": round(actual_ratio, 3),
                        "subject": p.label,
                    },
                )

            # Designated-zone rule is useful only when the zone is intentionally
            # configured. A point close to the boundary is ignored to avoid jitter.
            inside = self._inside(p.box, designated, width, height)
            boundary_margin = 0.03
            cx = p.center[0] / max(1, width)
            cy = p.center[1] / max(1, height)
            near_boundary = (
                abs(cx - designated.x1) < boundary_margin
                or abs(cx - designated.x2) < boundary_margin
                or abs(cy - designated.y1) < boundary_margin
                or abs(cy - designated.y2) < boundary_margin
            )
            key = ("Outside designated area", p.track_id, None)
            if not inside and not near_boundary:
                active_keys.add(key)
                self._emit(
                    events, "Outside designated area", t, p.track_id,
                    min(0.90, p.confidence * 0.70 + actual_ratio * 0.30),
                    0.25,
                    {
                        "zone": designated.name,
                        "center_normalized": [round(cx, 3), round(cy, 3)],
                        "evidence_quality": round(actual_ratio, 3),
                        "subject": p.label,
                    },
                )

            # Orientation change: require an upright baseline and several frames
            # in the new orientation.
            ratio = p.height / max(1, p.width)
            self.orientation_baseline.setdefault(p.track_id, deque(maxlen=8))
            baseline = self.orientation_baseline[p.track_id]
            if len(baseline) < 5:
                baseline.append(ratio)
            median_base = sorted(baseline)[len(baseline) // 2]
            key = ("Product orientation change", p.track_id, None)
            if median_base > MOTION["orientation_upright_ratio"] and ratio < MOTION["orientation_flat_ratio"]:
                active_keys.add(key)
                self._emit(
                    events, "Product orientation change", t, p.track_id,
                    min(0.91, p.confidence * 0.70 + actual_ratio * 0.30),
                    0.30,
                    {
                        "baseline_aspect_ratio": round(median_base, 2),
                        "current_aspect_ratio": round(ratio, 2),
                        "evidence_quality": round(actual_ratio, 3),
                        "subject": p.label,
                    },
                )
            baseline.append(ratio)

        # Pairwise stacking analysis.
        for a in products:
            for b in products:
                if a.track_id == b.track_id:
                    continue

                ax1, ay1, ax2, ay2 = a.box
                bx1, by1, bx2, by2 = b.box

                # a is above b.
                if ay2 <= by1 + 0.12 * max(a.height, b.height):
                    overlap = self._overlap(a, b)
                    gap = max(0, by1 - ay2) / max(1, b.height)
                    support_ratio = overlap

                    # Incorrect stacking: clear lateral offset.
                    key = ("Incorrect stacking", a.track_id, b.track_id)
                    if overlap < 0.35 and gap <= 0.20:
                        active_keys.add(key)
                        self._emit(
                            events, "Incorrect stacking", t, a.track_id,
                            min(0.90, (a.confidence + b.confidence) / 2 * 0.70 + min(
                                self._actual_ratio(a), self._actual_ratio(b)
                            ) * 0.30),
                            0.45,
                            {
                                "related_track_id": b.track_id,
                                "horizontal_overlap": round(overlap, 2),
                                "vertical_gap_ratio": round(gap, 3),
                                "support_ratio": round(support_ratio, 2),
                                "evidence_quality": round(min(self._actual_ratio(a), self._actual_ratio(b)), 3),
                                "subject": a.label,
                            },
                        )

                    # Unstable stacking: very small support area, regardless of
                    # visual weight. We do not claim to know physical weight.
                    key = ("Unstable stacking", a.track_id, b.track_id)
                    if overlap < 0.20 and gap <= 0.25:
                        active_keys.add(key)
                        self._emit(
                            events, "Unstable stacking", t, a.track_id,
                            min(0.92, (a.confidence + b.confidence) / 2 * 0.70 + min(
                                self._actual_ratio(a), self._actual_ratio(b)
                            ) * 0.30),
                            0.55,
                            {
                                "related_track_id": b.track_id,
                                "horizontal_overlap": round(overlap, 2),
                                "vertical_gap_ratio": round(gap, 3),
                                "support_ratio": round(support_ratio, 2),
                                "evidence_quality": round(min(self._actual_ratio(a), self._actual_ratio(b)), 3),
                                "subject": a.label,
                            },
                        )

        # Person-product interaction: only when the product is moving and the
        # person is very close. It is a review signal, not a claim of unsafe intent.
        for w in people:
            for p in products:
                if self._near(w, p, 0.32) and p.history[-1].get("speed", 0) > MOTION["sequence_speed"]:
                    key = ("Unsafe person-product interaction", p.track_id, w.track_id)
                    active_keys.add(key)
                    self._emit(
                        events, "Unsafe person-product interaction", t, p.track_id,
                        min(0.88, (p.confidence + w.confidence) / 2 * 0.70 + min(
                            self._actual_ratio(p), self._actual_ratio(w)
                        ) * 0.30),
                        0.40,
                        {
                            "related_track_id": w.track_id,
                            "product_speed_px_s": round(p.history[-1].get("speed", 0), 1),
                            "evidence_quality": round(min(self._actual_ratio(p), self._actual_ratio(w)), 3),
                            "subject": p.label,
                        },
                    )

        # Loading sequence: only flag a genuine entry overlap. A second product
        # must have just entered the configured loading zone while another distinct
        # product is still moving. Merely having two products in the zone is normal.
        active = [p for p in products if self._inside(p.box, loading, width, height)]
        active_ids = {p.track_id for p in active}
        for p in products:
            inside_now = p.track_id in active_ids
            if inside_now and p.track_id not in self.loading_entry_time:
                self.loading_entry_time[p.track_id] = t
            elif not inside_now:
                self.loading_entry_time.pop(p.track_id, None)

        recent_entries = [
            p for p in active
            if t - self.loading_entry_time.get(p.track_id, t) <= 0.75
        ]
        moving = [
            p for p in active
            if p.history and p.history[-1].get("speed", 0) > MOTION["sequence_speed"]
        ]
        for newest in recent_entries:
            older_moving = [p for p in moving if p.track_id != newest.track_id]
            if not older_moving:
                continue
            older = max(older_moving, key=lambda x: x.last_time)
            key = ("Unsafe loading sequence", newest.track_id, older.track_id)
            active_keys.add(key)
            self._emit(
                events, "Unsafe loading sequence", t, newest.track_id,
                min(0.90, (newest.confidence + older.confidence) / 2 * 0.70 + min(
                    self._actual_ratio(newest), self._actual_ratio(older)
                ) * 0.30),
                0.50,
                {
                    "related_track_id": older.track_id,
                    "new_product_entry_age_s": round(t - self.loading_entry_time.get(newest.track_id, t), 2),
                    "active_products": len(active),
                    "moving_products": len(moving),
                    "evidence_quality": round(min(self._actual_ratio(newest), self._actual_ratio(older)), 3),
                    "subject": newest.label,
                },
            )

        self._clear_missing(active_keys)
        return events
