from dataclasses import dataclass
import os

RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

# The taxonomy is aligned to the challenge examples. The engine only reports a
# behaviour when its temporal/spatial evidence passes the configured gates.
PRODUCT_PROMPTS = [
    "cardboard box", "carton", "package", "parcel", "crate", "container",
    "mattress", "chair", "sofa", "table", "appliance", "furniture", "bag",
    "pallet", "wooden pallet",
    "person", "worker", "operator",
    "forklift", "pallet jack", "hand truck", "dolly", "cart", "trolley",
]
PERSON_NAMES = {"person", "worker", "operator", "employee", "human"}
EQUIPMENT_NAMES = {
    "pallet", "wooden pallet", "forklift", "pallet jack",
    "hand truck", "dolly", "cart", "trolley"
}

SCENARIOS = {
    "Dropping / impact": (
        "A product shows a rapid downward movement followed by a strong deceleration/impact-like stop.",
        "CRITICAL",
        "Pause handling, inspect the product and review the unloading/loading method before continuing.",
    ),
    "Dragging": (
        "A product moves predominantly horizontally along the floor while a person is nearby.",
        "HIGH",
        "Use a trolley, pallet truck or suitable handling equipment instead of dragging the product.",
    ),
    "Rough handling": (
        "A tracked product shows a sustained high-speed movement with a significant acceleration change.",
        "HIGH",
        "Slow the handling action and use controlled movement, especially at transfer points.",
    ),
    "Incorrect stacking": (
        "Two tracked products form a stack with insufficient horizontal support or a clearly offset placement.",
        "HIGH",
        "Re-stack products with stable support and adequate overlap.",
    ),
    "Unstable stacking": (
        "A stacked product has a large unsupported overhang or a small support ratio relative to its footprint.",
        "HIGH",
        "Stabilize the stack and ensure the product is fully supported before continuing.",
    ),
    "Outside designated area": (
        "A product is observed outside the configured designated handling area.",
        "MEDIUM",
        "Review the configured zone and move the product back into the designated handling area.",
    ),
    "Unsafe loading sequence": (
        "A new product enters the configured loading zone while another product is still moving.",
        "HIGH",
        "Complete the current placement before introducing another product into the active loading zone.",
    ),
    "Unsafe person-product interaction": (
        "A person enters a close interaction zone with a moving product in a way that warrants review.",
        "HIGH",
        "Review the handling interaction and maintain a controlled, safe movement path.",
    ),
    "Product orientation change": (
        "A tracked product changes from a sustained upright aspect ratio to a substantially flatter orientation.",
        "MEDIUM",
        "Review the product orientation and restore the specified orientation if required.",
    ),
    "Rolling / uncontrolled movement": (
        "A product shows sustained horizontal motion with geometry consistent with uncontrolled rolling.",
        "HIGH",
        "Stop uncontrolled rolling and reposition the product using approved handling equipment.",
    ),
}

@dataclass(frozen=True)
class Zone:
    name: str
    x1: float
    y1: float
    x2: float
    y2: float

def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default

DEFAULT_ZONES = {
    "loading_zone": Zone(
        "Loading zone",
        _float_env("GODREJ_LOADING_X1", 0.20),
        _float_env("GODREJ_LOADING_Y1", 0.20),
        _float_env("GODREJ_LOADING_X2", 0.80),
        _float_env("GODREJ_LOADING_Y2", 0.90),
    ),
    "designated_zone": Zone(
        "Designated handling area",
        _float_env("GODREJ_DESIGNATED_X1", 0.05),
        _float_env("GODREJ_DESIGNATED_Y1", 0.10),
        _float_env("GODREJ_DESIGNATED_X2", 0.95),
        _float_env("GODREJ_DESIGNATED_Y2", 0.95),
    ),
}

# Conservative defaults favour precision over noisy alerts.
MOTION = {
    "drag_horizontal_px_s": _float_env("GODREJ_DRAG_SPEED", 55),
    "drag_vertical_ratio": _float_env("GODREJ_DRAG_VERTICAL_RATIO", 0.55),
    "roll_horizontal_px_s": _float_env("GODREJ_ROLL_SPEED", 65),
    "drop_vertical_px_s": _float_env("GODREJ_DROP_VERTICAL_SPEED", 160),
    "drop_speed_px_s": _float_env("GODREJ_DROP_SPEED", 175),
    "impact_deceleration": _float_env("GODREJ_IMPACT_DECELERATION", 220),
    "rough_speed_change": _float_env("GODREJ_ROUGH_SPEED_CHANGE", 110),
    "rough_speed": _float_env("GODREJ_ROUGH_SPEED", 110),
    "sequence_speed": _float_env("GODREJ_SEQUENCE_SPEED", 35),
    "orientation_upright_ratio": _float_env("GODREJ_UPRIGHT_RATIO", 1.25),
    "orientation_flat_ratio": _float_env("GODREJ_FLAT_RATIO", 0.78),
}

TRACKING = {
    "max_missed_frames": _int_env("GODREJ_TRACK_MAX_MISSED", 8),
    "min_iou": _float_env("GODREJ_TRACK_MIN_IOU", 0.03),
    "distance_gate_ratio": _float_env("GODREJ_TRACK_DISTANCE_GATE", 0.12),
}

ENGINE = {
    "minimum_detection_confidence": _float_env("GODREJ_MIN_DETECTION_CONF", 0.35),
    "minimum_track_hits": _int_env("GODREJ_MIN_TRACK_HITS", 4),
    "continuous_confirmation_frames": _int_env("GODREJ_CONFIRM_FRAMES", 4),
    "event_cooldown_s": _float_env("GODREJ_EVENT_COOLDOWN", 8.0),
    "summary_behaviour_limit": 2,
}

def risk_color(risk: str) -> str:
    return {
        "LOW": "#45d6a8",
        "MEDIUM": "#f4c95d",
        "HIGH": "#ff984d",
        "CRITICAL": "#ff4d6d",
    }.get(risk, "#9aa9b2")
