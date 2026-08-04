"""Non-technical French main menu for the Windows launcher."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .interactive_recommendation import InteractiveRecommendationApp
from .inventory_editor import run_inventory_editor
from .user_management import BagAssistant, GuidedPrompts, SqliteUserDataStore, UserDataStore, UserManagementError


class PgaShootoutAssistant(GuidedPrompts):
    def __init__(
        self,
        *,
        user_dir: str | Path = "data/pga_shootout.sqlite",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        legacy_user_dir: str | Path = "data/user",
        input_fn=None,
        output_fn=print,
        recommendation_factory: Callable[..., object] = InteractiveRecommendationApp,
        inventory_editor_factory: Callable[..., int] = run_inventory_editor,
    ) -> None:
        super().__init__(input_fn, output_fn)
        path = Path(user_dir)
        self.store = (
            SqliteUserDataStore(path, catalog_path, legacy_user_dir=legacy_user_dir)
            if path.suffix.casefold() in {".sqlite", ".sqlite3", ".db"}
            else UserDataStore(path, catalog_path)
        )
        self.bags = BagAssistant(self.store, self.input, self.output)
        self.recommendation_factory = recommendation_factory
        self.inventory_editor_factory = inventory_editor_factory

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

        while True:
            choice = self.choose(
                "Que souhaitez-vous faire ?",
                ("inventory", "bags", "recommend", "quit"),
                lambda item: {
                    "inventory": "Gérer mon inventaire",
                    "bags": "Gérer mes sacs",
                    "recommend": "Tester un club dans un sac",
                    "quit": "Quitter",
                }[item],
                allow_back=False,
            )
            try:
                if choice == "quit":
                    self.output("À bientôt !")
                    return 0
                if choice == "inventory":
                    self._open_inventory_editor()
                elif choice == "bags":
                    self.bags.run()
                else:
                    self._recommend()
            except (UserManagementError, KeyError, ValueError, OSError) as error:
                self.output("L'opération n'a pas pu être terminée : " + self.store.french_error(error))

    def _open_inventory_editor(self) -> None:
        if not isinstance(self.store, SqliteUserDataStore):
            self.inventory_editor_factory()
        else:
            self.inventory_editor_factory(
                database_path=self.store.user_dir,
                catalog_path=self.store.catalog_path,
                legacy_user_dir=self.store.legacy_user_dir,
                manifest_path=self.store.manifest_path,
            )
        self.output("Retour au menu principal.")

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
