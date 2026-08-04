"""Focused visual inventory editor backed by the local SQLite profile.

The service and draft models are UI-independent so all persistence and validation
can be tested without opening a graphical window.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable
import unicodedata

from .inventory_status import analyze_inventory_status, render_inventory_status
from .storage import PgaDatabase
from .user_management import SqliteUserDataStore


UNKNOWN = "—"
UNKNOWN_CALCULATION = "Inconnu"

BRAND_ORDER = (
    "Corvid",
    "Forester",
    "Nautilus",
    "Palo",
    "Phoenix",
    "Ryusei",
    "Stanchion",
    "Willoughsby",
    "Mythical",
)
CLUB_TYPE_ORDER = ("Putter", "Driver", "Wood", "Hybrid", "Iron", "Wedge")

# Number of copies needed to upgrade *to* each regular level.  Reference tables:
# https://golfshootout.fandom.com/wiki/Rarity (and its per-rarity pages).
# This reference
# belongs to the editor: it is not written into or inferred as game mechanics
# by the catalog or Rule Engine.  Elite upgrades are intentionally absent
# because their copy requirements are not present in the versioned catalog.
CARD_REQUIREMENTS_BY_TARGET_LEVEL: dict[str, dict[int, int]] = {
    "Common": {2: 2, 3: 5, 4: 10, 5: 25, 6: 50, 7: 100, 8: 250, 9: 500, 10: 1_000, 11: 2_500, 12: 5_000},
    "Rare": {4: 5, 5: 10, 6: 25, 7: 50, 8: 100, 9: 250, 10: 500, 11: 1_000, 12: 2_500},
    "Epic": {6: 5, 7: 25, 8: 50, 9: 100, 10: 250, 11: 500, 12: 1_000},
    "Legendary": {8: 2, 9: 4, 10: 6, 11: 8, 12: 10},
    "Mythical": {10: 2, 11: 3, 12: 4},
}
CARD_REQUIREMENTS_SOURCE = "PGA TOUR Golf Shootout Wiki — rarity upgrade tables"


def alphabetical_key(value: str) -> str:
    """Return a stable, case- and accent-insensitive key for display sorting."""

    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def ordered_category_key(value: str, known_values: tuple[str, ...]) -> tuple[int, int, str]:
    """Place future unknown categories after known ones without ever failing."""

    try:
        return 0, known_values.index(value), ""
    except ValueError:
        return 1, len(known_values), alphabetical_key(value)


def cards_required_for_next_level(rarity: str, current_level: int | None) -> int | None:
    """Return the documented regular-level card threshold, if determinable."""

    if current_level is None:
        return None
    return CARD_REQUIREMENTS_BY_TARGET_LEVEL.get(rarity, {}).get(current_level + 1)


@dataclass(frozen=True)
class InventoryRow:
    club_id: str
    name: str
    brand: str
    club_type: str
    rarity: str
    unlock_level: int | None
    allowed_levels: tuple[int, ...]
    examined: bool
    owned: bool
    current_level: int | None
    cards_owned: int | None
    cards_required: int | None

    @property
    def next_threshold(self) -> int | None:
        if not self.owned:
            return None
        calculated = cards_required_for_next_level(self.rarity, self.current_level)
        # Preserve useful legacy observations until the user supplies a level.
        return self.cards_required if self.current_level is None else calculated

    @property
    def progression(self) -> str:
        if not self.owned or self.cards_owned is None or self.next_threshold is None:
            return UNKNOWN
        return f"{self.cards_owned} / {self.next_threshold}"

    @property
    def cards_remaining(self) -> int | None:
        if not self.owned or self.cards_owned is None or self.next_threshold is None:
            return None
        return max(self.next_threshold - self.cards_owned, 0)

    @property
    def upgrade_available(self) -> bool | None:
        if not self.owned or self.cards_owned is None or self.next_threshold is None:
            return None
        return self.cards_owned >= self.next_threshold

    @property
    def complete(self) -> bool:
        if not self.examined:
            return False
        if not self.owned:
            return True
        return all(value is not None for value in (self.current_level, self.cards_owned, self.next_threshold))

    @property
    def data_state(self) -> str:
        if not self.examined:
            return "Non examiné"
        return "Complet" if self.complete else "Incomplet"

    def as_change(self) -> dict[str, Any]:
        return {
            "club_id": self.club_id,
            "display_name": self.name,
            "unlocked": self.owned,
            "current_level": self.current_level,
            "cards_owned": self.cards_owned,
            "cards_required_for_next_upgrade": self.next_threshold,
        }


@dataclass(frozen=True)
class InventoryChangeSummary:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    level_changes: tuple[str, ...]
    card_changes: tuple[str, ...]

    def render(self) -> str:
        def line(label: str, values: tuple[str, ...]) -> str:
            return f"{label} : " + (", ".join(values) if values else "aucun")

        return "\n".join((
            line("Clubs ajoutés", self.added),
            line("Clubs retirés", self.removed),
            line("Niveaux modifiés", self.level_changes),
            line("Cartes modifiées", self.card_changes),
        ))


@dataclass(frozen=True)
class InventoryDashboard:
    owned_clubs: int
    known_levels: int
    incomplete_owned_clubs: int
    added_this_session: tuple[str, ...]
    level_changes: tuple[str, ...]
    blacksmith_owned: bool
    simulated_abilities: int
    official_abilities: int
    coverage_percent: float

    def render(self) -> str:
        return "\n".join((
            f"Clubs possédés : {self.owned_clubs}",
            f"Niveaux connus : {self.known_levels}",
            f"Clubs possédés encore incomplets : {self.incomplete_owned_clubs}",
            "Clubs ajoutés pendant cette session : " + (", ".join(self.added_this_session) or "aucun"),
            "Niveaux modifiés : " + (", ".join(self.level_changes) or "aucun"),
            f"Blacksmith possédé : {'oui' if self.blacksmith_owned else 'non'}",
            f"Couverture moteur : {self.simulated_abilities}/{self.official_abilities} ({self.coverage_percent:.2f} %)",
        ))


class InventoryEditorService:
    """Read-only catalog projection and atomic profile updates."""

    def __init__(
        self,
        database_path: str | Path = "data/pga_shootout.sqlite",
        *,
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        manifest_path: str | Path = "data/catalog/versions.json",
        legacy_user_dir: str | Path = "data/user",
        normalized_dir: str | Path = "data/normalized",
        raw_catalog_path: str | Path = "data/raw/pga_club_stats_extract_v2_2026-07-21.json",
    ) -> None:
        self.database_path = Path(database_path)
        self.catalog_path = Path(catalog_path)
        self.manifest_path = Path(manifest_path)
        self.legacy_user_dir = Path(legacy_user_dir)
        self.normalized_dir = Path(normalized_dir)
        self.raw_catalog_path = Path(raw_catalog_path)
        self.database = PgaDatabase(self.database_path)

    def initialize(self) -> None:
        SqliteUserDataStore(
            self.database_path,
            self.catalog_path,
            legacy_user_dir=self.legacy_user_dir,
            manifest_path=self.manifest_path,
        ).ensure_files()

    def load_rows(self) -> tuple[InventoryRow, ...]:
        with self.database.connect() as connection:
            version = connection.execute("SELECT version_id FROM catalog_versions WHERE is_current = 1").fetchone()[0]
            catalog_rows = connection.execute(
                """SELECT club_id, name, brand_id, type_id, rarity_id, unlocks_at
                   FROM clubs WHERE version_id = ? ORDER BY name COLLATE NOCASE""",
                (version,),
            ).fetchall()
            users = {row["club_id"]: row for row in connection.execute("SELECT * FROM user_clubs")}
            levels: dict[str, list[int]] = {}
            for row in connection.execute(
                "SELECT club_id, level_key FROM club_levels WHERE version_id = ? AND available = 1",
                (version,),
            ):
                if str(row["level_key"]).isdigit():
                    levels.setdefault(row["club_id"], []).append(int(row["level_key"]))
            brands = dict(connection.execute("SELECT brand_id, name FROM brands"))
            types = dict(connection.execute("SELECT type_id, name FROM club_types"))
            rarities = dict(connection.execute("SELECT rarity_id, name FROM rarities"))
        result = []
        for club in catalog_rows:
            user = users.get(club["club_id"])
            result.append(InventoryRow(
                club_id=club["club_id"], name=club["name"], brand=brands[club["brand_id"]],
                club_type=types[club["type_id"]], rarity=rarities[club["rarity_id"]],
                unlock_level=club["unlocks_at"], allowed_levels=tuple(sorted(levels.get(club["club_id"], ()))),
                examined=user is not None, owned=bool(user["unlocked"]) if user else False,
                current_level=user["current_level"] if user else None,
                cards_owned=user["cards_owned"] if user else None,
                cards_required=user["cards_required"] if user else None,
            ))
        return tuple(sorted(result, key=self.row_sort_key))

    @staticmethod
    def row_sort_key(row: InventoryRow) -> tuple[Any, ...]:
        return (
            *ordered_category_key(row.brand, BRAND_ORDER),
            *ordered_category_key(row.club_type, CLUB_TYPE_ORDER),
            alphabetical_key(row.name),
            row.club_id,
        )

    @staticmethod
    def filter_rows(rows: Iterable[InventoryRow], *, search: str = "", brand: str = "Tous", club_type: str = "Tous", rarity: str = "Toutes", ownership: str = "Tous", incomplete_only: bool = False) -> tuple[InventoryRow, ...]:
        needle = search.strip().casefold()
        result = []
        for row in rows:
            if needle and needle not in row.name.casefold():
                continue
            if brand != "Tous" and row.brand != brand:
                continue
            if club_type != "Tous" and row.club_type != club_type:
                continue
            if rarity != "Toutes" and row.rarity != rarity:
                continue
            if ownership == "Possédés" and not row.owned:
                continue
            if ownership == "Non possédés" and row.owned:
                continue
            if incomplete_only and row.complete:
                continue
            result.append(row)
        return tuple(sorted(result, key=InventoryEditorService.row_sort_key))

    def validate(self, rows: Iterable[InventoryRow]) -> dict[str, str]:
        rows = tuple(rows)
        errors: dict[str, str] = {}
        ids = [row.club_id for row in rows]
        duplicates = {club_id for club_id in ids if ids.count(club_id) > 1}
        errors.update({club_id: "Ce club apparaît plusieurs fois." for club_id in duplicates})
        for row in rows:
            error = self._row_error(row)
            if error:
                errors[row.club_id] = error
        return errors

    @staticmethod
    def _row_error(row: InventoryRow) -> str | None:
        if not row.owned:
            if any(value is not None for value in (row.current_level, row.cards_owned)):
                return "Un club non possédé ne doit pas conserver de niveau ou de cartes."
            return None
        if row.current_level is not None and row.current_level not in row.allowed_levels:
            allowed = ", ".join(str(value) for value in row.allowed_levels)
            return f"Niveau indisponible pour ce club. Valeurs possibles : {allowed}."
        if row.cards_owned is not None and row.cards_owned < 0:
            return "Les cartes possédées doivent être positives ou égales à zéro."
        return None

    def validate_bags(self) -> tuple[str, ...]:
        errors = []
        with self.database.connect() as connection:
            version = connection.execute("SELECT version_id FROM catalog_versions WHERE is_current = 1").fetchone()[0]
            official = {row[0] for row in connection.execute("SELECT club_id FROM clubs WHERE version_id = ?", (version,))}
            for bag_id, name in connection.execute("SELECT bag_id, name FROM user_bags"):
                clubs = [row[0] for row in connection.execute("SELECT club_id FROM user_bag_clubs WHERE bag_id = ? ORDER BY position", (bag_id,))]
                if len(clubs) != 5 or len(set(clubs)) != 5:
                    errors.append(f"Le sac « {name} » doit contenir cinq clubs différents.")
                if any(club_id not in official for club_id in clubs):
                    errors.append(f"Le sac « {name} » contient un club absent du catalogue.")
        return tuple(errors)

    @staticmethod
    def summarize(original: Iterable[InventoryRow], edited: Iterable[InventoryRow]) -> InventoryChangeSummary:
        before = {row.club_id: row for row in original}
        added, removed, levels, cards = [], [], [], []
        for row in edited:
            old = before[row.club_id]
            if not old.owned and row.owned:
                added.append(row.name)
            if old.owned and not row.owned:
                removed.append(row.name)
            if old.current_level != row.current_level:
                levels.append(f"{row.name} ({old.current_level if old.current_level is not None else 'inconnu'} → {row.current_level if row.current_level is not None else 'inconnu'})")
            if old.cards_owned != row.cards_owned:
                cards.append(row.name)
        return InventoryChangeSummary(tuple(added), tuple(removed), tuple(levels), tuple(cards))

    @staticmethod
    def changed_rows(original: Iterable[InventoryRow], edited: Iterable[InventoryRow]) -> tuple[InventoryRow, ...]:
        before = {row.club_id: row for row in original}
        return tuple(row for row in edited if row != before[row.club_id])

    def save(self, original: Iterable[InventoryRow], edited: Iterable[InventoryRow]) -> tuple[Path, InventoryChangeSummary, InventoryDashboard]:
        original, edited = tuple(original), tuple(edited)
        errors = self.validate(edited)
        bag_errors = self.validate_bags()
        if errors or bag_errors:
            detail = next(iter(errors.values()), bag_errors[0] if bag_errors else "Données invalides.")
            raise ValueError(detail)
        changes = self.changed_rows(original, edited)
        if not changes:
            raise ValueError("Aucune modification à enregistrer.")
        summary = self.summarize(original, edited)
        backup = self.database.apply_inventory_batch(tuple(row.as_change() for row in changes), source="visual_inventory_editor")
        return backup, summary, self.dashboard(summary)

    def dashboard(self, summary: InventoryChangeSummary) -> InventoryDashboard:
        rows = self.load_rows()
        owned = tuple(row for row in rows if row.owned)
        status = analyze_inventory_status(
            user_dir=self.database_path,
            normalized_dir=self.normalized_dir,
            raw_catalog_path=self.raw_catalog_path,
        )
        blacksmith = next(row for row in rows if row.club_id == "blacksmith")
        return InventoryDashboard(
            owned_clubs=len(owned), known_levels=sum(row.current_level is not None for row in owned),
            incomplete_owned_clubs=sum(not row.complete for row in owned),
            added_this_session=summary.added, level_changes=summary.level_changes,
            blacksmith_owned=blacksmith.owned, simulated_abilities=status.simulated_abilities,
            official_abilities=status.official_abilities, coverage_percent=status.inventory_coverage_percent,
        )

    def unsupported_report(self) -> str:
        status = analyze_inventory_status(
            user_dir=self.database_path,
            normalized_dir=self.normalized_dir,
            raw_catalog_path=self.raw_catalog_path,
        )
        return render_inventory_status(status)


class InventoryEditorApp:
    """Small Tkinter table dedicated exclusively to inventory maintenance."""

    COLUMNS = ("owned", "name", "brand", "type", "rarity", "unlock", "level", "cards", "required", "progression", "remaining", "upgrade", "state", "error")
    EDITABLE_COLUMNS = {7: "current_level", 8: "cards_owned"}

    def __init__(self, service: InventoryEditorService, root=None) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.service = service
        self.service.initialize()
        self.root = root or tk.Tk()
        self.root.title("PGA Shootout — Gérer mon inventaire")
        self.root.geometry("1500x780")
        self.original = self.service.load_rows()
        self.rows = {row.club_id: row for row in self.original}
        self.errors: dict[str, str] = {}
        self.search = tk.StringVar()
        self.brand = tk.StringVar(value="Tous")
        self.club_type = tk.StringVar(value="Tous")
        self.rarity = tk.StringVar(value="Toutes")
        self.ownership = tk.StringVar(value="Tous")
        self.incomplete = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Double-cliquez sur Niveau ou Cartes pour modifier. Une cellule vide signifie « inconnu ».")
        self._build()
        self._refresh()

    def _build(self) -> None:
        tk, ttk = self.tk, self.ttk
        filters = ttk.Frame(self.root, padding=10)
        filters.pack(fill="x")
        ttk.Label(filters, text="Rechercher :").grid(row=0, column=0, sticky="w")
        search = ttk.Entry(filters, textvariable=self.search, width=28)
        search.grid(row=0, column=1, padx=(4, 14))
        search.bind("<KeyRelease>", lambda _event: self._refresh())
        for column, (label, variable, values) in enumerate((
            ("Marque", self.brand, ["Tous", *sorted({row.brand for row in self.original})]),
            ("Type", self.club_type, ["Tous", *sorted({row.club_type for row in self.original})]),
            ("Rareté", self.rarity, ["Toutes", *sorted({row.rarity for row in self.original})]),
            ("Possession", self.ownership, ["Tous", "Possédés", "Non possédés"]),
        ), start=2):
            ttk.Label(filters, text=label + " :").grid(row=0, column=column * 2 - 2, sticky="e")
            box = ttk.Combobox(filters, textvariable=variable, values=values, state="readonly", width=15)
            box.grid(row=0, column=column * 2 - 1, padx=(4, 10))
            box.bind("<<ComboboxSelected>>", lambda _event: self._refresh())
        ttk.Checkbutton(filters, text="Données incomplètes uniquement", variable=self.incomplete, command=self._refresh).grid(row=1, column=0, columnspan=3, pady=(8, 0), sticky="w")

        frame = ttk.Frame(self.root, padding=(10, 0))
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=self.COLUMNS, show="headings", selectmode="browse")
        labels = {"owned": "Possédé", "name": "Club", "brand": "Marque", "type": "Type", "rarity": "Rareté", "unlock": "Déblocage", "level": "Niveau", "cards": "Cartes possédées", "required": "Seuil suivant", "progression": "Progression", "remaining": "Cartes restantes", "upgrade": "Amélioration disponible", "state": "Données", "error": "Erreur"}
        widths = {"owned": 70, "name": 150, "brand": 105, "type": 90, "rarity": 90, "unlock": 80, "level": 75, "cards": 110, "required": 95, "progression": 100, "remaining": 105, "upgrade": 135, "state": 100, "error": 330}
        for column in self.COLUMNS:
            self.tree.heading(column, text=labels[column])
            self.tree.column(column, width=widths[column], minwidth=55, anchor="center" if column not in {"name", "error"} else "w")
        self.tree.tag_configure("error", background="#ffe4e4")
        self.tree.tag_configure("dirty", background="#fff5cc")
        vertical = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<Double-1>", self._edit_cell)

        buttons = ttk.Frame(self.root, padding=10)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Enregistrer toutes les modifications", command=self._save).pack(side="left")
        ttk.Button(buttons, text="Annuler les modifications non enregistrées", command=self._cancel).pack(side="left", padx=8)
        ttk.Button(buttons, text="Voir les capacités non prises en charge", command=self._show_report).pack(side="left")
        ttk.Label(buttons, textvariable=self.status, wraplength=680, justify="left").pack(side="right")

    def _visible_rows(self) -> tuple[InventoryRow, ...]:
        return self.service.filter_rows(
            self.rows.values(), search=self.search.get(), brand=self.brand.get(),
            club_type=self.club_type.get(), rarity=self.rarity.get(), ownership=self.ownership.get(),
            incomplete_only=self.incomplete.get(),
        )

    def _values(self, row: InventoryRow) -> tuple[str, ...]:
        upgrade = row.upgrade_available
        calculation_unknown = row.owned and (
            row.cards_owned is None or row.next_threshold is None
        )
        return (
            "☑" if row.owned else "☐", row.name, row.brand, row.club_type, row.rarity,
            str(row.unlock_level) if row.unlock_level is not None else UNKNOWN,
            str(row.current_level) if row.current_level is not None else UNKNOWN,
            str(row.cards_owned) if row.cards_owned is not None else UNKNOWN,
            str(row.next_threshold) if row.next_threshold is not None else (UNKNOWN_CALCULATION if row.owned else UNKNOWN),
            UNKNOWN_CALCULATION if calculation_unknown else row.progression,
            str(row.cards_remaining) if row.cards_remaining is not None else (UNKNOWN_CALCULATION if calculation_unknown else UNKNOWN),
            (UNKNOWN_CALCULATION if calculation_unknown else UNKNOWN) if upgrade is None else ("Oui" if upgrade else "Non"), row.data_state,
            self.errors.get(row.club_id, ""),
        )

    def _refresh(self) -> None:
        selected = self.tree.selection()
        vertical_position = self.tree.yview()[0] if self.tree.get_children() else 0.0
        horizontal_position = self.tree.xview()[0] if self.tree.get_children() else 0.0
        self.tree.delete(*self.tree.get_children())
        original = {row.club_id: row for row in self.original}
        for row in self._visible_rows():
            tags = ("error",) if row.club_id in self.errors else (("dirty",) if row != original[row.club_id] else ())
            self.tree.insert("", "end", iid=row.club_id, values=self._values(row), tags=tags)
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
        self.tree.yview_moveto(vertical_position)
        self.tree.xview_moveto(horizontal_position)
        self.status.set(f"{len(self._visible_rows())} club(s) affiché(s) sur {len(self.rows)}.")

    def _click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if item and column == "#1":
            row = self.rows[item]
            self.rows[item] = replace(row, examined=True, owned=not row.owned, current_level=row.current_level if not row.owned else None, cards_owned=row.cards_owned if not row.owned else None, cards_required=row.cards_required if not row.owned else None)
            self.errors.pop(item, None)
            self._refresh()

    def _edit_cell(self, event) -> None:
        item = self.tree.identify_row(event.y)
        column_number = int(self.tree.identify_column(event.x).lstrip("#") or 0)
        if not item or column_number not in self.EDITABLE_COLUMNS:
            return
        self._begin_edit(item, column_number)

    @staticmethod
    def next_edit_target(visible_ids: tuple[str, ...], item: str, column_number: int, navigation: str) -> tuple[str, int] | None:
        if item not in visible_ids:
            return None
        if navigation == "stay":
            return None
        position = visible_ids.index(item)
        if navigation == "next_cell" and column_number == 7:
            return item, 8
        if position + 1 >= len(visible_ids):
            return None
        return visible_ids[position + 1], 7 if navigation == "next_cell" else column_number

    def _begin_edit(self, item: str, column_number: int) -> None:
        if not self.tree.exists(item) or column_number not in self.EDITABLE_COLUMNS:
            return
        field = self.EDITABLE_COLUMNS[column_number]
        x, y, width, height = self.tree.bbox(item, f"#{column_number}")
        entry = self.ttk.Entry(self.tree)
        current = getattr(self.rows[item], field)
        entry.insert(0, "" if current is None else str(current))
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        self.select_existing_text(entry)
        finished = False

        def finish(_event=None, *, navigation: str | None = None) -> str | None:
            nonlocal finished
            if finished:
                return "break" if navigation else None
            finished = True
            visible_ids = tuple(row.club_id for row in self._visible_rows())
            target = self.next_edit_target(visible_ids, item, column_number, navigation) if navigation else None
            text = entry.get().strip()
            if text and (not text.isdigit()):
                self.errors[item] = "Saisissez un nombre entier ou laissez vide."
            else:
                value = None if not text else int(text)
                self.rows[item] = replace(self.rows[item], examined=True, **{field: value})
                self.errors.pop(item, None)
            entry.destroy()
            self._refresh()
            if target and self.tree.exists(target[0]):
                self.tree.selection_set(target[0])
                self.tree.see(target[0])
                self.root.after_idle(lambda: self._begin_edit(*target))
            elif navigation == "stay" and self.tree.exists(item):
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.focus_set()
            return "break" if navigation else None

        entry.bind("<Return>", lambda event: finish(event, navigation="stay"))
        entry.bind("<Tab>", lambda event: finish(event, navigation="next_cell"))
        entry.bind("<FocusOut>", finish)

        def cancel(_event=None) -> None:
            nonlocal finished
            finished = True
            entry.destroy()
            self._refresh()

        entry.bind("<Escape>", cancel)

    @staticmethod
    def select_existing_text(entry) -> None:
        """Select the current value once, while preserving normal later clicks."""

        entry.selection_range(0, "end")
        entry.icursor("end")

    def _cancel(self) -> None:
        from tkinter import messagebox

        if messagebox.askyesno("Annuler", "Annuler toutes les modifications non enregistrées ?"):
            self.rows = {row.club_id: row for row in self.original}
            self.errors.clear()
            self._refresh()
            self.status.set("Modifications non enregistrées annulées.")

    def _save(self) -> None:
        from tkinter import messagebox

        edited = tuple(self.rows.values())
        self.errors = self.service.validate(edited)
        bag_errors = self.service.validate_bags()
        if self.errors or bag_errors:
            self._refresh()
            messagebox.showerror("Données à corriger", next(iter(self.errors.values()), bag_errors[0]))
            return
        summary = self.service.summarize(self.original, edited)
        if not self.service.changed_rows(self.original, edited):
            messagebox.showinfo("Inventaire", "Aucune modification à enregistrer.")
            return
        if not messagebox.askyesno("Confirmer l'enregistrement", summary.render() + "\n\nEnregistrer toutes ces modifications ?"):
            return
        try:
            backup, _summary, dashboard = self.service.save(self.original, edited)
        except Exception as error:
            messagebox.showerror("Enregistrement impossible", str(error))
            return
        self.original = self.service.load_rows()
        self.rows = {row.club_id: row for row in self.original}
        self.errors.clear()
        self._refresh()
        messagebox.showinfo("Inventaire enregistré", dashboard.render() + f"\n\nSauvegarde : {backup}")

    def _show_report(self) -> None:
        window = self.tk.Toplevel(self.root)
        window.title("Capacités non prises en charge")
        text = self.tk.Text(window, wrap="word", width=120, height=40)
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.service.unsupported_report())
        text.configure(state="disabled")

    def run(self) -> int:
        self.root.mainloop()
        return 0


def run_inventory_editor(**kwargs) -> int:
    service = InventoryEditorService(**kwargs)
    try:
        return InventoryEditorApp(service).run()
    except Exception as error:
        # A launcher-friendly fallback: no Python traceback is shown to the player.
        try:
            from tkinter import messagebox
            messagebox.showerror("PGA Shootout", "L'éditeur d'inventaire n'a pas pu démarrer.\n\n" + str(error))
        except Exception:
            print("L'éditeur d'inventaire n'a pas pu démarrer : " + str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(run_inventory_editor())
