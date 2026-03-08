from __future__ import annotations


class HappyPathProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, *, prompt_bundle: dict[str, str], grounding: dict[str, object]) -> dict[str, object]:
        self.calls += 1
        requested_slots = grounding["slot_requirements"]
        slots = []
        for requested_slot in requested_slots:
            slots.append(
                {
                    "slot_key": requested_slot["slot_key"],
                    "meal_title": f"{requested_slot['meal_type'].title()} Provider Meal {self.calls}",
                    "summary": "Provider-backed deterministic suggestion.",
                    "uses_on_hand": ["broccoli"],
                    "missing_key_ingredients": ["lemons"],
                    "reason_codes": ["USES_ON_HAND", "AVOIDS_RECENT_REPEAT"],
                    "explanations": [
                        {
                            "code": "USES_ON_HAND",
                            "message": "Uses broccoli already on hand.",
                            "source_refs": ["inventory:broccoli"],
                        }
                    ],
                    "grocery_impact_hint": "Add lemons if desired.",
                }
            )
        return {
            "fallback_mode": "none",
            "warnings": [],
            "data_completeness_note": None,
            "slots": slots,
        }


class InvalidPayloadProvider:
    def generate(self, *, prompt_bundle: dict[str, str], grounding: dict[str, object]) -> dict[str, object]:
        return {"slots": [{"slot_key": "bad"}]}


class ExplodingProvider:
    def generate(self, *, prompt_bundle: dict[str, str], grounding: dict[str, object]) -> dict[str, object]:
        raise KeyError("deterministic worker failure")
