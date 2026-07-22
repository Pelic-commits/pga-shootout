"""User-owned data models, loading and validation.

This module deliberately has no dependency on simulation rules or ability
semantics. It only references stable identifiers from the official catalog.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .loader import load_raw_json


class UserDataError(ValueError):
    pass


@dataclass(frozen=True)
class UserAccount:
    player_name: str
    player_level: int
    fedex_reward_target_level: int
    current_tier: int
    tier_6_decision: str
    priority_club_id: str
    available_bag_slots: int
    free_to_play: bool
    real_money_spending: bool
    opens_all_available_ad_funded_packs: bool
    uses_special_balls: bool


@dataclass(frozen=True)
class InventoryEntry:
    club_id: str
    display_name: str
    unlocked: bool
    current_level: int | None
    cards_owned: int
    cards_required_for_next_upgrade: int
    observed_at: str
    source: str

    @property
    def upgrade_available(self) -> bool:
        return self.cards_owned >= self.cards_required_for_next_upgrade


@dataclass(frozen=True)
class Inventory:
    inventory_complete: bool
    observed_at: str
    source: str
    entries: tuple[InventoryEntry, ...]

    def get(self, club_id: str) -> InventoryEntry | None:
        """Return None for an unlisted club; absence never means locked."""
        return next((entry for entry in self.entries if entry.club_id == club_id), None)


@dataclass(frozen=True)
class PreferenceItem:
    criterion: str
    preference: str
    weight: float | None


@dataclass(frozen=True)
class UserPreferences:
    priorities: tuple[PreferenceItem, ...]
    free_to_play_required: bool
    paid_special_balls_allowed: bool


@dataclass(frozen=True)
class SavedBag:
    identifier: str
    name: str
    status: str
    club_ids: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class UserObservation:
    identifier: str
    status: str
    club_ids: tuple[str, ...]
    text: str
    unresolved_reference: str | None = None


@dataclass(frozen=True)
class UserDataBundle:
    account: UserAccount
    inventory: Inventory
    preferences: UserPreferences
    bags: tuple[SavedBag, ...]
    observations: tuple[UserObservation, ...]


@dataclass(frozen=True)
class UserDataValidationReport:
    valid: bool
    inventory_entries: int
    inventory_complete: bool
    resolved_references: tuple[str, ...]
    unknown_references: tuple[str, ...]
    duplicate_references: tuple[str, ...]
    upgrade_available: tuple[str, ...]
    saved_bags: int
    unresolved_notes: tuple[str, ...]
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ClubCatalogIndex:
    def __init__(self, clubs: Mapping[str, Mapping[str, Any]]) -> None:
        self.clubs = dict(clubs)
        self._ids_by_name = {str(club["name"]).casefold(): club_id for club_id, club in clubs.items()}

    @classmethod
    def load(cls, path: str | Path) -> "ClubCatalogIndex":
        data = load_raw_json(path)
        clubs = data.get("clubs") if isinstance(data, dict) else None
        if not isinstance(clubs, dict):
            raise UserDataError("official catalog clubs must be an object keyed by stable identifier")
        return cls(clubs)

    def contains(self, club_id: str) -> bool:
        return club_id in self.clubs

    def resolve(self, reference: str) -> str | None:
        if reference in self.clubs:
            return reference
        return self._ids_by_name.get(reference.casefold())


def _read_object(path: Path) -> dict[str, Any]:
    data = load_raw_json(path)
    if not isinstance(data, dict):
        raise UserDataError(f"{path.name} must contain a JSON object")
    return data


def load_user_data(user_dir: str | Path) -> UserDataBundle:
    root = Path(user_dir)
    account_data = _read_object(root / "account.json")
    inventory_data = _read_object(root / "inventory.json")
    preferences_data = _read_object(root / "preferences.json")
    bags_data = _read_object(root / "bags.json")
    observations_data = _read_object(root / "observations.json")

    account = UserAccount(
        player_name=str(account_data["player_name"]),
        player_level=int(account_data["player_level"]),
        fedex_reward_target_level=int(account_data["fedex_reward_target_level"]),
        current_tier=int(account_data["current_tier"]),
        tier_6_decision=str(account_data["tier_6_decision"]),
        priority_club_id=str(account_data["priority_club_goal"]["club_id"]),
        available_bag_slots=int(account_data["available_bag_slots"]),
        free_to_play=bool(account_data["free_to_play"]),
        real_money_spending=bool(account_data["real_money_spending"]),
        opens_all_available_ad_funded_packs=bool(account_data["opens_all_available_ad_funded_packs"]),
        uses_special_balls=bool(account_data["uses_special_balls"]),
    )
    loaded_entries = []
    for item in inventory_data["entries"]:
        entry = InventoryEntry(
            club_id=str(item["club_id"]),
            display_name=str(item["display_name"]),
            unlocked=bool(item["unlocked"]),
            current_level=None if item.get("current_level") is None else int(item["current_level"]),
            cards_owned=int(item["cards_owned"]),
            cards_required_for_next_upgrade=int(item["cards_required_for_next_upgrade"]),
            observed_at=str(item["observed_at"]),
            source=str(item["source"]),
        )
        if bool(item["upgrade_available"]) != entry.upgrade_available:
            raise UserDataError(f"stored upgrade_available is inconsistent for {entry.club_id}")
        loaded_entries.append(entry)
    entries = tuple(loaded_entries)
    inventory = Inventory(
        inventory_complete=bool(inventory_data["inventory_complete"]),
        observed_at=str(inventory_data["observed_at"]),
        source=str(inventory_data["source"]),
        entries=entries,
    )
    preferences = UserPreferences(
        priorities=tuple(
            PreferenceItem(str(item["criterion"]), str(item["preference"]), item.get("weight"))
            for item in preferences_data["priorities"]
        ),
        free_to_play_required=bool(preferences_data["constraints"]["free_to_play_required"]),
        paid_special_balls_allowed=bool(preferences_data["constraints"]["paid_special_balls_allowed"]),
    )
    bags = tuple(
        SavedBag(
            identifier=str(item["id"]),
            name=str(item["name"]),
            status=str(item["status"]),
            club_ids=tuple(str(value) for value in item["club_ids"]),
            notes=tuple(str(value) for value in item.get("notes", [])),
        )
        for item in bags_data["bags"]
    )
    observations = tuple(
        UserObservation(
            identifier=str(item["id"]),
            status=str(item["status"]),
            club_ids=tuple(str(value) for value in item.get("club_ids", [])),
            text=str(item["text"]),
            unresolved_reference=item.get("unresolved_reference"),
        )
        for item in observations_data["observations"]
    )
    return UserDataBundle(account, inventory, preferences, bags, observations)


def _duplicates(values: list[str]) -> set[str]:
    return {value for value in values if values.count(value) > 1}


def validate_user_data(bundle: UserDataBundle, catalog: ClubCatalogIndex) -> UserDataValidationReport:
    errors: list[str] = []
    all_references = [bundle.account.priority_club_id]
    inventory_ids = [entry.club_id for entry in bundle.inventory.entries]
    all_references.extend(inventory_ids)
    all_references.extend(club_id for bag in bundle.bags for club_id in bag.club_ids)
    all_references.extend(club_id for item in bundle.observations for club_id in item.club_ids)

    duplicates = sorted(_duplicates(inventory_ids))
    if duplicates:
        errors.append("duplicate inventory club references")
    for entry in bundle.inventory.entries:
        if entry.cards_owned < 0 or entry.cards_required_for_next_upgrade <= 0:
            errors.append(f"invalid card counts for {entry.club_id}")
    for bag in bundle.bags:
        if len(bag.club_ids) != 5:
            errors.append(f"bag {bag.identifier} must contain exactly five clubs")
        if len(set(bag.club_ids)) != len(bag.club_ids):
            errors.append(f"bag {bag.identifier} contains duplicate clubs")
        if bag.status != "user_observed":
            errors.append(f"bag {bag.identifier} has unsupported status {bag.status}")
    allowed_observation_statuses = {
        "preference",
        "positive_observation",
        "negative_observation",
        "unresolved_note",
        "in_game_validation",
    }
    for observation in bundle.observations:
        if observation.status not in allowed_observation_statuses:
            errors.append(f"observation {observation.identifier} has unsupported status {observation.status}")
    for preference in bundle.preferences.priorities:
        if preference.weight is not None:
            errors.append(f"preference {preference.criterion} has an unvalidated numeric weight")

    resolved = sorted({club_id for club_id in all_references if catalog.contains(club_id)})
    unknown = sorted({club_id for club_id in all_references if not catalog.contains(club_id)})
    if unknown:
        errors.append("unknown official club references: " + ", ".join(unknown))

    upgrades = tuple(entry.club_id for entry in bundle.inventory.entries if entry.upgrade_available)
    unresolved_notes = tuple(
        item.unresolved_reference
        for item in bundle.observations
        if item.status == "unresolved_note" and item.unresolved_reference
    )
    return UserDataValidationReport(
        valid=not errors,
        inventory_entries=len(bundle.inventory.entries),
        inventory_complete=bundle.inventory.inventory_complete,
        resolved_references=tuple(resolved),
        unknown_references=tuple(unknown),
        duplicate_references=tuple(duplicates),
        upgrade_available=upgrades,
        saved_bags=len(bundle.bags),
        unresolved_notes=unresolved_notes,
        errors=tuple(errors),
    )


def serialize_stable(value: Any) -> str:
    """Serialize dataclasses or plain values deterministically."""
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
