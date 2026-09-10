import unittest
from engine.risk import classify
from engine.config import SCENARIOS
from engine.tracker import GreedyTracker
from engine.assistant import SupervisorAssistant


class CoreTests(unittest.TestCase):
    def test_taxonomy_has_at_least_ten_behaviours(self):
        self.assertGreaterEqual(len(SCENARIOS), 10)

    def test_risk_is_bounded_and_ordered(self):
        low = classify("LOW", .5, evidence_quality=.8).score
        critical = classify("CRITICAL", 1, 5, 1, .95).score
        self.assertGreaterEqual(low, 0)
        self.assertLessEqual(critical, 100)
        self.assertLess(low, critical)

    def test_tracker_keeps_identity_through_small_motion(self):
        tr = GreedyTracker(max_distance=100)
        a = tr.update(
            [{"box": [0, 0, 50, 50], "label": "carton", "confidence": .9}],
            0.0,
        )[0].track_id
        b = tr.update(
            [{"box": [5, 2, 55, 52], "label": "carton", "confidence": .9}],
            0.1,
        )[0].track_id
        self.assertEqual(a, b)

    def test_tracker_does_not_cross_assign_semantic_classes(self):
        tr = GreedyTracker(max_distance=100)
        first = tr.update(
            [
                {"box": [0, 0, 50, 50], "label": "carton", "confidence": .9},
                {"box": [60, 0, 110, 50], "label": "person", "confidence": .9},
            ],
            0.0,
        )
        ids = {x.label: x.track_id for x in first}
        second = tr.update(
            [
                {"box": [2, 0, 52, 50], "label": "person", "confidence": .9},
                {"box": [58, 0, 108, 50], "label": "carton", "confidence": .9},
            ],
            0.1,
        )
        self.assertEqual({x.label: x.track_id for x in second}, ids)

    def test_assistant_surfaces_at_most_two_behaviours(self):
        incidents = [
            {
                "behaviour": "Dragging",
                "risk": "HIGH",
                "risk_score": 70,
                "timestamp": 4.2,
                "explanation": "horizontal movement",
                "recommended_action": "use equipment",
            },
            {
                "behaviour": "Dragging",
                "risk": "HIGH",
                "risk_score": 72,
                "timestamp": 8.4,
                "explanation": "horizontal movement",
                "recommended_action": "use equipment",
            },
            {
                "behaviour": "Dropping / impact",
                "risk": "CRITICAL",
                "risk_score": 90,
                "timestamp": 12.1,
                "explanation": "downward motion followed by deceleration",
                "recommended_action": "inspect product",
            },
            {
                "behaviour": "Rough handling",
                "risk": "HIGH",
                "risk_score": 69,
                "timestamp": 15.5,
                "explanation": "high acceleration",
                "recommended_action": "slow handling",
            },
        ]
        result = SupervisorAssistant().answer("shift brief", incidents)
        self.assertLessEqual(len(result["findings"]), 2)
        self.assertIn("Dropping / impact", result["summary"])


if __name__ == "__main__":
    unittest.main()
