"""Guided management of user-owned JSON data.

This module deliberately stays outside the rule engine.  It selects official
club identifiers from the catalog, persists the existing user-data formats,
and validates every mutation through the existing validators.
"""

from __future__ import annotations

import json
import shutil
import unicodedata
from collections.abc import Callable, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .user_data import ClubCatalogIndex, UserDataError, load_user_data, validate_user_data


InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]
USER_FILENAMES = (
    "account.json",
    "inventory.json",
    "preferences.json",
    "bags.json",
    "observations.json",
)


class UserManagementError(ValueError):
    """A user-facing persistence or validation error."""


def _today() -> str:
    return date.today().isoformat()


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _slug(value: str) -> str:
    normalized = _normalized(value)
    result = "".join(character if character.isalnum() else "_" for character in normalized)
    return "_".join(part for part in result.split("_") if part) or "mon_sac"


class UserDataStore:
    """Safe mutations over the five existing JSON files."""

    def __init__(self, user_dir: str | Path, catalog_path: str | Path) -> None:
        self.user_dir = Path(user_dir)
        self.catalog_path = Path(catalog_path)
        self.catalog = ClubCatalogIndex.load(self.catalog_path)

    def ensure_files(self) -> tuple[str, ...]:
        """Create only missing files, without replacing existing data."""
        missing = tuple(name for name in USER_FILENAMES if not (self.user_dir / name).exists())
        if not missing:
            return ()
        self.backup()
        self.user_dir.mkdir(parents=True, exist_ok=True)
        defaults = self._default_documents()
        for name in missing:
            self._write_json(self.user_dir / name, defaults[name])
        self.validate_or_raise()
        return missing

    def reset_after_confirmation(self) -> Path:
        """Replace all files with valid empty defaults after the UI confirms."""
        backup = self.backup()
        self.user_dir.mkdir(parents=True, exist_ok=True)
        for name, document in self._default_documents().items():
            self._write_json(self.user_dir / name, document)
        self.validate_or_raise()
        return backup

    def backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination = self.user_dir / "backups" / timestamp
        destination.mkdir(parents=True, exist_ok=False)
        for name in USER_FILENAMES:
            source = self.user_dir / name
            if source.exists():
                shutil.copy2(source, destination / name)
        return destination

    def validation(self):
        bundle = load_user_data(self.user_dir)
        return validate_user_data(bundle, self.catalog)

    def validate_or_raise(self) -> None:
        try:
            report = self.validation()
        except (KeyError, TypeError, ValueError, OSError, UserDataError) as error:
            raise UserManagementError(self.french_error(error)) from error
        if not report.valid:
            raise UserManagementError(" ".join(self.french_error(error) for error in report.errors))

    def search_clubs(self, query: str) -> tuple[tuple[str, str], ...]:
        words = tuple(part for part in _normalized(query).split() if part)
        if not words:
            return ()
        matches = []
        for club_id, club in self.catalog.clubs.items():
            name = str(club["name"])
            searchable = _normalized(name)
            if all(word in searchable for word in words):
                matches.append((club_id, name))
        return tuple(sorted(matches, key=lambda item: item[1].casefold()))

    def inventory_documents(self) -> list[dict[str, Any]]:
        return list(self._read_json("inventory.json")["entries"])

    def owned_inventory(self) -> tuple[dict[str, Any], ...]:
        return tuple(item for item in self.inventory_documents() if bool(item["unlocked"]))

    def save_inventory_entry(
        self,
        club_id: str,
        *,
        current_level: int | None,
        cards_owned: int,
        cards_required: int,
        unlocked: bool = True,
    ) -> tuple[Path, bool]:
        if not self.catalog.contains(club_id):
            raise UserManagementError("Ce club n'existe pas dans le catalogue officiel.")
        if current_level is not None and current_level < 1:
            raise UserManagementError("Le niveau doit être positif ou rester inconnu.")
        if cards_owned < 0 or cards_required <= 0:
            raise UserManagementError("Les cartes possédées doivent être positives ou nulles et le seuil doit être positif.")
        document = self._read_json("inventory.json")
        entries = list(document["entries"])
        official_name = str(self.catalog.clubs[club_id]["name"])
        entry = {
            "club_id": club_id,
            "display_name": official_name,
            "unlocked": unlocked,
            "current_level": current_level,
            "cards_owned": cards_owned,
            "cards_required_for_next_upgrade": cards_required,
            "upgrade_available": cards_owned >= cards_required,
            "observed_at": _today(),
            "source": "guided_user_entry",
        }
        existing = next((index for index, item in enumerate(entries) if item["club_id"] == club_id), None)
        if existing is None:
            entries.append(entry)
        else:
            entries[existing] = entry
        document["entries"] = entries
        document["observed_at"] = _today()
        document["source"] = "guided_user_entry"
        backup = self._commit_document("inventory.json", document)
        return backup, entry["upgrade_available"]

    def mark_not_owned(self, club_id: str) -> Path:
        document = self._read_json("inventory.json")
        entry = next((item for item in document["entries"] if item["club_id"] == club_id), None)
        if entry is None:
            raise UserManagementError("Ce club n'est pas enregistré dans votre inventaire.")
        entry["unlocked"] = False
        entry["observed_at"] = _today()
        entry["source"] = "guided_user_entry"
        document["observed_at"] = _today()
        return self._commit_document("inventory.json", document)

    def delete_inventory_entry(self, club_id: str) -> Path:
        document = self._read_json("inventory.json")
        filtered = [item for item in document["entries"] if item["club_id"] != club_id]
        if len(filtered) == len(document["entries"]):
            raise UserManagementError("Ce club n'est pas enregistré dans votre inventaire.")
        document["entries"] = filtered
        document["observed_at"] = _today()
        return self._commit_document("inventory.json", document)

    def bag_documents(self) -> list[dict[str, Any]]:
        return list(self._read_json("bags.json")["bags"])

    def save_bag(self, name: str, club_ids: Sequence[str], *, bag_id: str | None = None) -> tuple[Path, str]:
        clean_name = name.strip()
        if not clean_name:
            raise UserManagementError("Le sac doit avoir un nom.")
        if len(club_ids) != 5 or len(set(club_ids)) != 5:
            raise UserManagementError("Un sac doit contenir exactement cinq clubs différents.")
        owned = {item["club_id"] for item in self.owned_inventory()}
        if any(club_id not in owned for club_id in club_ids):
            raise UserManagementError("Tous les clubs du sac doivent être marqués comme possédés.")

        document = self._read_json("bags.json")
        bags = list(document["bags"])
        if bag_id is None:
            base = _slug(clean_name)
            existing_ids = {item["id"] for item in bags}
            bag_id = base
            suffix = 2
            while bag_id in existing_ids:
                bag_id = f"{base}_{suffix}"
                suffix += 1
            bags.append({
                "id": bag_id,
                "name": clean_name,
                "status": "user_observed",
                "club_ids": list(club_ids),
                "notes": ["Sac créé avec l'assistant guidé."],
            })
        else:
            index = next((index for index, item in enumerate(bags) if item["id"] == bag_id), None)
            if index is None:
                raise UserManagementError("Ce sac n'existe plus.")
            previous_notes = bags[index].get("notes", [])
            bags[index] = {
                "id": bag_id,
                "name": clean_name,
                "status": "user_observed",
                "club_ids": list(club_ids),
                "notes": previous_notes,
            }
        document["bags"] = bags
        document["observed_at"] = _today()
        document["source"] = "guided_user_entry"
        backup = self._commit_document("bags.json", document)
        return backup, bag_id

    def delete_bag(self, bag_id: str) -> Path:
        document = self._read_json("bags.json")
        bags = [item for item in document["bags"] if item["id"] != bag_id]
        if len(bags) == len(document["bags"]):
            raise UserManagementError("Ce sac n'existe plus.")
        document["bags"] = bags
        document["observed_at"] = _today()
        return self._commit_document("bags.json", document)

    def _commit_document(self, filename: str, document: dict[str, Any]) -> Path:
        backup = self.backup()
        target = self.user_dir / filename
        existed = target.exists()
        previous = target.read_bytes() if existed else b""
        try:
            self._write_json(target, document)
            self.validate_or_raise()
        except Exception:
            if existed:
                target.write_bytes(previous)
            elif target.exists():
                target.unlink()
            raise
        return backup

    def _read_json(self, filename: str) -> dict[str, Any]:
        try:
            with (self.user_dir / filename).open("r", encoding="utf-8") as stream:
                value = json.load(stream)
        except (OSError, json.JSONDecodeError) as error:
            raise UserManagementError(self.french_error(error)) from error
        if not isinstance(value, dict):
            raise UserManagementError(f"Le fichier {filename} n'a pas la structure attendue.")
        return value

    @staticmethod
    def _write_json(path: Path, document: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary.replace(path)

    def _default_documents(self) -> dict[str, dict[str, Any]]:
        priority_id = "meteor" if self.catalog.contains("meteor") else sorted(self.catalog.clubs)[0]
        priority_name = str(self.catalog.clubs[priority_id]["name"])
        common = {"schema_version": "1.0.0", "observed_at": _today(), "source": "guided_first_run"}
        return {
            "account.json": {
                **common,
                "player_name": "Joueur",
                "player_level": 1,
                "fedex_reward_target_level": 1,
                "current_tier": 1,
                "tier_6_decision": "undecided",
                "tier_6_decision_note": "",
                "mythics_available_by_tier": {},
                "priority_club_goal": {"club_id": priority_id, "display_name": priority_name},
                "available_bag_slots": 5,
                "free_to_play": True,
                "real_money_spending": False,
                "opens_all_available_ad_funded_packs": False,
                "uses_special_balls": False,
            },
            "inventory.json": {**common, "inventory_complete": False, "entries": []},
            "preferences.json": {
                **common,
                "priorities": [],
                "constraints": {"free_to_play_required": False, "paid_special_balls_allowed": False},
            },
            "bags.json": {**common, "bags": []},
            "observations.json": {**common, "observations": []},
        }

    @staticmethod
    def french_error(error: object) -> str:
        text = str(error)
        replacements = {
            "Cannot load JSON from": "Un fichier personnel est illisible :",
            "duplicate inventory club references": "Un club apparaît plusieurs fois dans l'inventaire.",
            "unknown official club references": "Des clubs ne sont pas reconnus dans le catalogue officiel",
            "must contain exactly five clubs": "doit contenir exactement cinq clubs",
            "contains duplicate clubs": "contient un club en double",
            "stored upgrade_available is inconsistent": "Le statut d'amélioration est incohérent",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return text or "Les données utilisateur ne sont pas valides."


class GuidedPrompts:
    def __init__(self, input_fn: InputFunction | None = None, output_fn: OutputFunction = print) -> None:
        self.input = input_fn or input
        self.output = output_fn

    def choose(self, title: str, options: Sequence[Any], label: Callable[[Any], str], *, allow_back: bool = True):
        while True:
            self.output("")
            self.output(title)
            for index, option in enumerate(options, start=1):
                self.output(f"{index} - {label(option)}")
            if allow_back:
                self.output("0 - Retour")
            value = self.input("> ").strip()
            if allow_back and value == "0":
                return None
            if value.isdigit() and 1 <= int(value) <= len(options):
                return options[int(value) - 1]
            self.output("Choix invalide. Saisissez le numéro d'une option proposée.")

    def yes_no(self, title: str) -> bool:
        choice = self.choose(title, (True, False), lambda value: "Oui" if value else "Non", allow_back=False)
        return bool(choice)

    def non_negative_integer(self, title: str, *, minimum: int = 0) -> int:
        while True:
            self.output(title)
            value = self.input("> ").strip()
            if value.isdigit() and int(value) >= minimum:
                return int(value)
            self.output(f"Saisie invalide. Entrez un nombre entier supérieur ou égal à {minimum}.")


class InventoryAssistant(GuidedPrompts):
    def __init__(self, store: UserDataStore, input_fn: InputFunction | None = None, output_fn: OutputFunction = print) -> None:
        super().__init__(input_fn, output_fn)
        self.store = store

    def run(self) -> None:
        while True:
            choice = self.choose(
                "Gestion de mes clubs",
                ("list", "edit", "not_owned", "delete", "back"),
                lambda item: {
                    "list": "Afficher mes clubs",
                    "edit": "Ajouter ou modifier un club",
                    "not_owned": "Marquer un club comme non possédé",
                    "delete": "Supprimer une entrée ajoutée par erreur",
                    "back": "Retour au menu principal",
                }[item],
                allow_back=False,
            )
            if choice == "back":
                return
            if choice == "list":
                self.list_inventory()
            elif choice == "edit":
                self.edit_club()
            elif choice == "not_owned":
                self.change_ownership(delete=False)
            else:
                self.change_ownership(delete=True)

    def list_inventory(self) -> None:
        entries = self.store.inventory_documents()
        self.output("")
        self.output("Mes clubs")
        if not entries:
            self.output("Aucun club n'est encore enregistré.")
            return
        for item in sorted(entries, key=lambda value: value["display_name"].casefold()):
            level = item["current_level"] if item["current_level"] is not None else "inconnu"
            owned = "possédé" if item["unlocked"] else "non possédé"
            upgrade = " — amélioration disponible" if item["upgrade_available"] else ""
            self.output(f"- {item['display_name']} : niveau {level}, {owned}{upgrade}")

    def edit_club(self) -> bool:
        while True:
            self.output("")
            self.output("Recherchez le club par son nom (0 pour annuler) :")
            query = self.input("> ").strip()
            if query == "0":
                return False
            matches = self.store.search_clubs(query)
            if not matches:
                self.output("Aucun club trouvé. Essayez une autre partie du nom.")
                continue
            selected = self.choose("Club trouvé :", matches, lambda item: item[1])
            if selected is None:
                return False
            break
        club_id, name = selected
        current = next((item for item in self.store.inventory_documents() if item["club_id"] == club_id), None)
        if current:
            self.output(f"Les informations actuelles de {name} vont être remplacées.")
        self.output("Niveau actuel (laissez vide s'il est inconnu) :")
        while True:
            value = self.input("> ").strip()
            if not value:
                level = None
                break
            if value.isdigit() and int(value) >= 1:
                level = int(value)
                break
            self.output("Niveau invalide. Entrez un nombre positif ou laissez vide.")
        cards = self.non_negative_integer("Nombre de cartes possédées :")
        required = self.non_negative_integer("Cartes nécessaires à la prochaine amélioration :", minimum=1)
        backup, upgrade = self.store.save_inventory_entry(
            club_id,
            current_level=level,
            cards_owned=cards,
            cards_required=required,
        )
        self.output(f"{name} a été enregistré et les données ont été validées.")
        self.output("Amélioration disponible." if upgrade else "Amélioration non disponible.")
        self.output(f"Sauvegarde créée dans : {backup}")
        return True

    def change_ownership(self, *, delete: bool) -> None:
        entries = self.store.inventory_documents()
        if not entries:
            self.output("Aucun club n'est enregistré.")
            return
        selected = self.choose("Choisissez le club :", entries, lambda item: item["display_name"])
        if selected is None:
            return
        action = "supprimer cette entrée" if delete else "marquer ce club comme non possédé"
        if not self.yes_no(f"Confirmer : {action} ?"):
            self.output("Aucune modification effectuée.")
            return
        backup = (
            self.store.delete_inventory_entry(selected["club_id"])
            if delete
            else self.store.mark_not_owned(selected["club_id"])
        )
        self.output("Modification enregistrée et validée.")
        self.output(f"Sauvegarde créée dans : {backup}")


class BagAssistant(GuidedPrompts):
    def __init__(self, store: UserDataStore, input_fn: InputFunction | None = None, output_fn: OutputFunction = print) -> None:
        super().__init__(input_fn, output_fn)
        self.store = store

    def run(self) -> None:
        while True:
            choice = self.choose(
                "Gestion de mes sacs",
                ("list", "create", "edit", "delete", "back"),
                lambda item: {
                    "list": "Afficher mes sacs",
                    "create": "Créer un nouveau sac",
                    "edit": "Modifier un sac existant",
                    "delete": "Supprimer un sac",
                    "back": "Retour au menu principal",
                }[item],
                allow_back=False,
            )
            if choice == "back":
                return
            if choice == "list":
                self.list_bags()
            elif choice == "create":
                self.create_or_edit()
            elif choice == "edit":
                self.select_for_edit()
            else:
                self.delete()

    def list_bags(self) -> None:
        bags = self.store.bag_documents()
        if not bags:
            self.output("Aucun sac n'est encore enregistré.")
            return
        for bag in bags:
            names = [str(self.store.catalog.clubs[club_id]["name"]) for club_id in bag["club_ids"]]
            self.output(f"- {bag['name']} : " + " / ".join(names))

    def select_for_edit(self) -> bool:
        bags = self.store.bag_documents()
        if not bags:
            self.output("Aucun sac n'est encore enregistré.")
            return False
        selected = self.choose("Choisissez le sac à modifier :", bags, lambda item: item["name"])
        return False if selected is None else self.create_or_edit(selected)

    def create_or_edit(self, existing: dict[str, Any] | None = None) -> bool:
        owned = list(self.store.owned_inventory())
        if len(owned) < 5:
            self.output("Il faut enregistrer au moins cinq clubs possédés avant de créer un sac.")
            return False
        if existing:
            self.output(f"Nom du sac (Entrée pour conserver « {existing['name']} ») :")
        else:
            self.output("Nom du nouveau sac :")
        name = self.input("> ").strip()
        if existing and not name:
            name = existing["name"]
        if not name:
            self.output("Le nom ne peut pas être vide.")
            return False
        selected_ids: list[str] = []
        for position in range(1, 6):
            available = [item for item in owned if item["club_id"] not in selected_ids]
            selected = self.choose(
                f"Position {position} — choisissez un club :",
                available,
                lambda item: item["display_name"],
            )
            if selected is None:
                self.output("Création du sac annulée. Aucune donnée n'a été modifiée.")
                return False
            selected_ids.append(selected["club_id"])
        backup, bag_id = self.store.save_bag(
            name,
            selected_ids,
            bag_id=existing["id"] if existing else None,
        )
        self.output(f"Le sac « {name} » a été enregistré et validé.")
        self.output("Ordre : " + " / ".join(str(self.store.catalog.clubs[item]["name"]) for item in selected_ids))
        self.output(f"Sauvegarde créée dans : {backup}")
        return bool(bag_id)

    def delete(self) -> None:
        bags = self.store.bag_documents()
        if not bags:
            self.output("Aucun sac n'est encore enregistré.")
            return
        selected = self.choose("Choisissez le sac à supprimer :", bags, lambda item: item["name"])
        if selected is None:
            return
        if not self.yes_no(f"Supprimer définitivement « {selected['name']} » ?"):
            self.output("Aucune modification effectuée.")
            return
        backup = self.store.delete_bag(selected["id"])
        self.output("Le sac a été supprimé et les données restantes ont été validées.")
        self.output(f"Sauvegarde créée dans : {backup}")
