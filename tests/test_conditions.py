import unittest

from pga_shootout.engine import RuleEngine
from pga_shootout.models import Condition, Effect
from tests.helpers import make_game_state


class ConditionTests(unittest.TestCase):
    def test_data_driven_club_attribute_condition(self):
        effect = Effect(
            "add_stat",
            {"stat": "power", "amount": 4},
            condition=Condition(
                "current_club_attribute_equals",
                {"field": "brand", "value": "Fixture Brand"},
                "current club has required brand",
            ),
            source="brand bonus fixture",
        )
        entry = RuleEngine().evaluate(make_game_state(), [effect]).explain[0]
        self.assertTrue(entry.applied)
        self.assertEqual(entry.condition, "current club has required brand")


if __name__ == "__main__":
    unittest.main()
