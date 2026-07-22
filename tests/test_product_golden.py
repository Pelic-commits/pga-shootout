import unittest
from pathlib import Path

from pga_shootout.bag_comparison import compare_saved_bags, render_bag_comparison
from pga_shootout.bag_evaluation import build_game_state
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import load_user_data


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
GOLDEN = ROOT / "tests" / "golden"


class ProductGoldenTests(unittest.TestCase):
    def test_reference_bag_comparison_is_stable(self):
        comparison = compare_saved_bags(
            "par3_divebomb",
            "par3_high_flight",
            level=12,
            current_position=1,
            mode=EvaluationMode.PARTIAL,
            user_dir=USER_DIR,
            catalog_path=CATALOG,
        )
        expected = (GOLDEN / "compare_par3_reference_position1.txt").read_text(encoding="utf-8")
        self.assertEqual(render_bag_comparison(comparison) + "\n", expected)

    def test_reference_bag_rarity_explain_is_stable(self):
        bag = load_user_data(USER_DIR).bags[0]
        state = build_game_state(bag, CATALOG, 12, "divebomb")
        effect = next(
            ability.effects[0]
            for ability in state.bag.get("steadfast").club.abilities
            if ability.text == "bag_rarity_boost"
        )
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
        expected = (GOLDEN / "par3_divebomb_rarity_explain.txt").read_text(encoding="utf-8")
        self.assertEqual(render_explain_entries(result.explain) + "\n", expected)


if __name__ == "__main__":
    unittest.main()
