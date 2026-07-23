import contextlib
import io
import unittest
from pathlib import Path
from unittest import mock

from pga_shootout.cli import main
from pga_shootout.interactive_recommendation import InteractiveRecommendationApp
from pga_shootout.user_data import load_user_data


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
GOLDEN = ROOT / "tests" / "golden" / "interactive_cyclotron_summary.txt"


class InteractiveRecommendationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = load_user_data(USER_DIR)
        bag = bundle.bags[0]
        eligible = [
            item for item in bundle.inventory.entries
            if item.unlocked and item.club_id not in bag.club_ids
        ]
        cls.cyclotron_choice = str(
            next(index for index, item in enumerate(eligible, start=1) if item.club_id == "cyclotron")
        )

    def run_app(self, answers):
        remaining = iter(answers)
        output = []
        app = InteractiveRecommendationApp(
            user_dir=USER_DIR,
            catalog_path=CATALOG,
            input_fn=lambda _prompt: next(remaining),
            output_fn=output.append,
        )
        exit_code = app.run()
        return exit_code, output

    def scenario_answers(self, *, details="2", placement=None):
        values = ["1", self.cyclotron_choice, "2", "12", details]
        if placement is not None:
            values.append(str(placement))
        return values

    def test_guided_navigation_reaches_five_placement_result(self):
        exit_code, output = self.run_app(self.scenario_answers())
        rendered = "\n".join(output)

        self.assertEqual(exit_code, 0)
        self.assertIn("Choisissez un sac :", rendered)
        self.assertIn("Choisissez un club à tester :", rendered)
        self.assertIn("Choisissez le mode :", rendered)
        self.assertIn("Niveau de scénario :", rendered)
        self.assertEqual(sum(line.startswith("Placement ") for line in output), 5)

    def test_invalid_choices_are_reprompted_without_crashing(self):
        answers = [
            "x", "1",
            "0", self.cyclotron_choice,
            "9", "2",
            "", "12",
            "peut-être", "2",
        ]
        exit_code, output = self.run_app(answers)
        rendered = "\n".join(output)

        self.assertEqual(exit_code, 0)
        self.assertGreaterEqual(rendered.count("Choix invalide"), 4)
        self.assertIn("Niveau invalide", rendered)

    def test_categories_and_warnings_are_displayed_in_plain_french(self):
        _, output = self.run_app(self.scenario_answers())
        rendered = "\n".join(output)

        self.assertIn("Catégorie : amélioration sans contrepartie", rendered)
        self.assertIn("Catégorie : compromis", rendered)
        self.assertIn("Avertissements :", rendered)
        self.assertIn("Le niveau 12 est hypothétique", rendered)
        self.assertIn("L'inventaire utilisateur est incomplet", rendered)
        self.assertIn("Aucun score global n'a été calculé", rendered)

    def test_detailed_explain_can_be_opened_for_one_placement(self):
        exit_code, output = self.run_app(self.scenario_answers(details="1", placement=2))
        rendered = "\n".join(output)

        self.assertEqual(exit_code, 0)
        self.assertIn("Explain détaillé — placement 2", rendered)
        self.assertIn("Position évaluée 1 — Divebomb", rendered)
        self.assertIn("Position évaluée 5 — Sunstorm", rendered)
        self.assertIn("ADD_STAT", rendered)

    def test_cli_command_uses_the_same_interactive_application(self):
        answers = iter(self.scenario_answers())
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)):
            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "recommend-interactive",
                        "--user-dir", str(USER_DIR),
                        "--catalog", str(CATALOG),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Assistant de placement PGA Shootout", output.getvalue())
        self.assertIn("Placement 5 — Sunstorm → Cyclotron", output.getvalue())

    def test_interactive_summary_matches_golden(self):
        _, output = self.run_app(self.scenario_answers())
        prefixes = (
            "Assistant de placement",
            "Choisissez un sac",
            "Choisissez un club",
            "Choisissez le mode",
            "Niveau de scénario",
            "Placement ",
            "Catégorie :",
            "Aucun score",
            "Plusieurs placements",
            "Afficher les explications",
        )
        stable = "\n".join(line for line in output if line.startswith(prefixes)) + "\n"
        self.assertEqual(stable, GOLDEN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
