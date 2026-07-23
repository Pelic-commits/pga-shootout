"""Non-technical French main menu for the Windows launcher."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .interactive_recommendation import InteractiveRecommendationApp
from .user_management import BagAssistant, GuidedPrompts, InventoryAssistant, UserDataStore, UserManagementError


class PgaShootoutAssistant(GuidedPrompts):
    def __init__(
        self,
        *,
        user_dir: str | Path = "data/user",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        input_fn=None,
        output_fn=print,
        recommendation_factory: Callable[..., object] = InteractiveRecommendationApp,
    ) -> None:
        super().__init__(input_fn, output_fn)
        self.store = UserDataStore(user_dir, catalog_path)
        self.inventory = InventoryAssistant(self.store, self.input, self.output)
        self.bags = BagAssistant(self.store, self.input, self.output)
        self.recommendation_factory = recommendation_factory

    def run(self) -> int:
        self.output("PGA Shootout Assistant")
        self.output("=" * 40)
        try:
            created = self.store.ensure_files()
            if created:
                self.output("Les fichiers personnels manquants ont été créés sans modifier les fichiers existants.")
            self.store.validate_or_raise()
        except UserManagementError as error:
            self.output("Vos données personnelles ne peuvent pas être utilisées :")
            self.output(str(error))
            if not self.yes_no("Créer une sauvegarde puis repartir avec des fichiers personnels vides et valides ?"):
                self.output("Aucune donnée existante n'a été remplacée.")
                return 1
            backup = self.store.reset_after_confirmation()
            self.output(f"Les anciens fichiers ont été sauvegardés dans : {backup}")

        report = self.store.validation()
        if len(self.store.owned_inventory()) < 5 or report.saved_bags == 0:
            self._offer_first_setup()

        while True:
            choice = self.choose(
                "Que souhaitez-vous faire ?",
                ("recommend", "inventory", "bags", "validate", "scenario", "quit"),
                lambda item: {
                    "recommend": "Tester un nouveau club dans un sac",
                    "inventory": "Consulter ou modifier mes clubs",
                    "bags": "Créer ou modifier un sac",
                    "validate": "Vérifier mes données",
                    "scenario": "Tester un club en mode Scénario",
                    "quit": "Quitter",
                }[item],
                allow_back=False,
            )
            try:
                if choice == "quit":
                    self.output("À bientôt !")
                    return 0
                if choice == "recommend":
                    self._recommend()
                elif choice == "inventory":
                    self.inventory.run()
                elif choice == "bags":
                    self.bags.run()
                elif choice == "validate":
                    self._validate()
                else:
                    self._recommend(forced_mode="scenario")
            except (UserManagementError, KeyError, ValueError, OSError) as error:
                self.output("L'opération n'a pas pu être terminée : " + self.store.french_error(error))

    def _offer_first_setup(self) -> None:
        self.output("")
        self.output("Votre configuration n'est pas encore suffisante pour créer et analyser un sac.")
        if not self.yes_no("Lancer maintenant l'assistant de première configuration ?"):
            return
        while len(self.store.owned_inventory()) < 5:
            remaining = 5 - len(self.store.owned_inventory())
            self.output(f"Ajoutez encore {remaining} club(s) possédé(s).")
            if not self.inventory.edit_club():
                self.output("La première configuration pourra être reprise depuis le menu principal.")
                return
        self.output("Vous avez au moins cinq clubs. Créons votre premier sac.")
        if not self.bags.create_or_edit():
            self.output("La création du sac pourra être reprise depuis le menu principal.")
            return
        self._validate()
        if self.yes_no("Tester maintenant un nouveau club ?"):
            self._recommend()

    def _recommend(self, *, forced_mode: str | None = None) -> None:
        if not self.store.bag_documents():
            self.output("Créez d'abord un sac depuis le menu principal.")
            return
        app = self.recommendation_factory(
            user_dir=self.store.user_dir,
            catalog_path=self.store.catalog_path,
            input_fn=self.input,
            output_fn=self.output,
            forced_mode=forced_mode,
        )
        app.run()
        self.output("")
        self.output("Retour au menu principal.")

    def _validate(self) -> None:
        report = self.store.validation()
        if report.valid:
            self.output(
                f"Données valides : {report.inventory_entries} club(s) enregistré(s), "
                f"{report.saved_bags} sac(s)."
            )
            if not report.inventory_complete:
                self.output("Votre inventaire est déclaré incomplet : les clubs absents restent simplement inconnus.")
        else:
            self.output("Certaines informations doivent être corrigées :")
            for error in report.errors:
                self.output("- " + self.store.french_error(error))
