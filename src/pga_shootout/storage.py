"""SQLite application storage with lossless JSON migration adapters."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .catalog_store import initialize_catalog_database
from .user_data import (
    BagReferenceProfile,
    Inventory,
    InventoryEntry,
    PreferenceItem,
    SavedBag,
    UserAccount,
    UserDataBundle,
    UserObservation,
    UserPreferences,
    _reference_profile,
)


USER_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS user_profile (
    profile_id INTEGER PRIMARY KEY CHECK(profile_id = 1),
    player_name TEXT NOT NULL,
    player_level INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory_state (
    profile_id INTEGER PRIMARY KEY REFERENCES user_profile(profile_id),
    inventory_complete INTEGER NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_clubs (
    club_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    unlocked INTEGER NOT NULL,
    current_level INTEGER,
    cards_owned INTEGER,
    cards_required INTEGER,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    examined_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_bags (
    bag_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    notes_json TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_bag_clubs (
    bag_id TEXT NOT NULL REFERENCES user_bags(bag_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK(position BETWEEN 1 AND 5),
    club_id TEXT NOT NULL,
    PRIMARY KEY(bag_id, position),
    UNIQUE(bag_id, club_id)
);
CREATE TABLE IF NOT EXISTS user_preferences (
    profile_id INTEGER PRIMARY KEY REFERENCES user_profile(profile_id),
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_observations (
    observation_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    club_ids_json TEXT NOT NULL,
    text TEXT NOT NULL,
    unresolved_reference TEXT,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_change_log (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    changed_at TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT
);
CREATE TABLE IF NOT EXISTS migration_runs (
    migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    source_dir TEXT NOT NULL,
    backup_path TEXT NOT NULL,
    preview_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);
"""


USER_FILENAMES = ("account.json", "inventory.json", "preferences.json", "bags.json", "observations.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class MigrationPreview:
    source_dir: str
    files: tuple[dict[str, Any], ...]
    inventory_entries: int
    owned_clubs: int
    known_levels: int
    bags: int
    bag_positions: int
    preferences: int
    observations: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MigrationResult:
    migrated: bool
    backup_path: str
    preview: MigrationPreview
    inventory_entries: int
    bags: int
    bag_positions: int
    observations: int
    validation_messages: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def migration_preview(user_dir: str | Path) -> MigrationPreview:
    root = Path(user_dir)
    documents = {name: json.loads((root / name).read_text(encoding="utf-8")) for name in USER_FILENAMES}
    inventory = documents["inventory.json"].get("entries", [])
    bags = documents["bags.json"].get("bags", [])
    return MigrationPreview(
        source_dir=str(root.resolve()),
        files=tuple(
            {"name": name, "sha256": _file_sha(root / name), "bytes": (root / name).stat().st_size}
            for name in USER_FILENAMES
        ),
        inventory_entries=len(inventory),
        owned_clubs=sum(bool(item.get("unlocked")) for item in inventory),
        known_levels=sum(item.get("current_level") is not None for item in inventory),
        bags=len(bags),
        bag_positions=sum(len(item.get("club_ids", [])) for item in bags),
        preferences=len(documents["preferences.json"].get("priorities", [])),
        observations=len(documents["observations.json"].get("observations", [])),
    )


def backup_json_user_data(user_dir: str | Path) -> Path:
    root = Path(user_dir)
    destination = root / "backups" / ("sqlite-migration-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    destination.mkdir(parents=True, exist_ok=False)
    for name in USER_FILENAMES:
        shutil.copy2(root / name, destination / name)
    return destination


class PgaDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize_catalog(self, manifest_path: str | Path = "data/catalog/versions.json") -> None:
        initialize_catalog_database(self.path, manifest_path)
        with self.connect() as connection:
            connection.executescript(USER_SCHEMA)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def has_user_profile(self) -> bool:
        with self.connect() as connection:
            return connection.execute("SELECT 1 FROM user_profile WHERE profile_id = 1").fetchone() is not None

    def migrate_json_user(self, user_dir: str | Path, *, replace: bool = False) -> MigrationResult:
        preview = migration_preview(user_dir)
        backup = backup_json_user_data(user_dir)
        documents = {
            name: json.loads((Path(user_dir) / name).read_text(encoding="utf-8")) for name in USER_FILENAMES
        }
        started = _now()
        with self.connect() as connection:
            if connection.execute("SELECT 1 FROM user_profile WHERE profile_id = 1").fetchone() and not replace:
                raise ValueError("A user profile already exists; explicit replacement is required")
            if replace:
                self._clear_user(connection)
            self._insert_documents(connection, documents)
            completed = _now()
            result_counts = self._user_counts(connection)
            messages = self._migration_messages(preview, result_counts)
            messages.extend(self._payload_messages(connection, documents))
            result = MigrationResult(
                migrated=not messages,
                backup_path=str(backup),
                preview=preview,
                inventory_entries=result_counts["inventory_entries"],
                bags=result_counts["bags"],
                bag_positions=result_counts["bag_positions"],
                observations=result_counts["observations"],
                validation_messages=tuple(messages),
            )
            connection.execute(
                """INSERT INTO migration_runs(
                    started_at, completed_at, source_dir, backup_path, preview_json, result_json
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (started, completed, str(Path(user_dir).resolve()), str(backup), _json(preview.as_dict()), _json(result.as_dict())),
            )
            if messages:
                raise ValueError("Migration validation failed: " + "; ".join(messages))
            connection.execute(
                "INSERT INTO user_change_log(changed_at, entity_type, entity_id, action, before_json, after_json) VALUES (?, ?, ?, ?, ?, ?)",
                (completed, "profile", "1", "migrate_json", None, _json(preview.as_dict())),
            )
            connection.commit()
            return result

    def _insert_documents(self, connection: sqlite3.Connection, documents: Mapping[str, Mapping[str, Any]]) -> None:
        account = documents["account.json"]
        inventory = documents["inventory.json"]
        preferences = documents["preferences.json"]
        bags = documents["bags.json"]
        observations = documents["observations.json"]
        connection.execute(
            "INSERT INTO user_profile VALUES (1, ?, ?, ?, ?)",
            (account["player_name"], int(account["player_level"]), account.get("observed_at", _now()), _json(account)),
        )
        connection.execute(
            "INSERT INTO inventory_state VALUES (1, ?, ?, ?)",
            (int(bool(inventory["inventory_complete"])), inventory["observed_at"], inventory["source"]),
        )
        for item in inventory.get("entries", []):
            self._insert_user_club(connection, item)
        for bag in bags.get("bags", []):
            connection.execute(
                "INSERT INTO user_bags VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    bag["id"], bag["name"], bag["status"], _json(bag.get("notes", [])),
                    bags.get("observed_at", _now()), bags.get("source", "json_migration"), _json(bag),
                ),
            )
            for position, club_id in enumerate(bag.get("club_ids", []), start=1):
                connection.execute("INSERT INTO user_bag_clubs VALUES (?, ?, ?)", (bag["id"], position, club_id))
        connection.execute("INSERT INTO user_preferences VALUES (1, ?)", (_json(preferences),))
        for item in observations.get("observations", []):
            connection.execute(
                "INSERT INTO user_observations VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item["id"], item["status"], _json(item.get("club_ids", [])), item["text"],
                    item.get("unresolved_reference"), _json(item),
                ),
            )

    @staticmethod
    def _insert_user_club(connection: sqlite3.Connection, item: Mapping[str, Any]) -> None:
        observed_at = str(item.get("observed_at") or _now())
        connection.execute(
            "INSERT INTO user_clubs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item["club_id"], item["display_name"], int(bool(item["unlocked"])), item.get("current_level"),
                item.get("cards_owned"), item.get("cards_required_for_next_upgrade"), observed_at,
                item.get("source", "json_migration"), observed_at, _json(item),
            ),
        )

    @staticmethod
    def _clear_user(connection: sqlite3.Connection) -> None:
        for table in (
            "user_bag_clubs", "user_bags", "user_clubs", "user_observations",
            "user_preferences", "inventory_state", "user_profile",
        ):
            connection.execute(f"DELETE FROM {table}")

    @staticmethod
    def _user_counts(connection: sqlite3.Connection) -> dict[str, int]:
        return {
            "inventory_entries": connection.execute("SELECT COUNT(*) FROM user_clubs").fetchone()[0],
            "bags": connection.execute("SELECT COUNT(*) FROM user_bags").fetchone()[0],
            "bag_positions": connection.execute("SELECT COUNT(*) FROM user_bag_clubs").fetchone()[0],
            "observations": connection.execute("SELECT COUNT(*) FROM user_observations").fetchone()[0],
        }

    @staticmethod
    def _migration_messages(preview: MigrationPreview, counts: Mapping[str, int]) -> list[str]:
        messages = []
        for field in ("inventory_entries", "bags", "bag_positions", "observations"):
            if getattr(preview, field) != counts[field]:
                messages.append(f"{field}: expected {getattr(preview, field)}, stored {counts[field]}")
        return messages

    @staticmethod
    def _payload_messages(connection: sqlite3.Connection, documents: Mapping[str, Mapping[str, Any]]) -> list[str]:
        """Verify every migrated source document, not only aggregate counts."""
        messages: list[str] = []
        checks = (
            ("account", _json(documents["account.json"]), connection.execute("SELECT payload_json FROM user_profile WHERE profile_id = 1").fetchone()[0]),
            ("preferences", _json(documents["preferences.json"]), connection.execute("SELECT payload_json FROM user_preferences WHERE profile_id = 1").fetchone()[0]),
        )
        messages.extend(f"{name}: migrated payload differs" for name, expected, actual in checks if expected != actual)
        for table, key, items in (
            ("user_clubs", "club_id", documents["inventory.json"].get("entries", [])),
            ("user_bags", "id", documents["bags.json"].get("bags", [])),
            ("user_observations", "id", documents["observations.json"].get("observations", [])),
        ):
            id_column = {"user_clubs": "club_id", "user_bags": "bag_id", "user_observations": "observation_id"}[table]
            for item in items:
                row = connection.execute(f"SELECT payload_json FROM {table} WHERE {id_column} = ?", (item[key],)).fetchone()
                if row is None or row[0] != _json(item):
                    messages.append(f"{table}/{item[key]}: migrated payload differs")
        return messages

    def load_user_bundle(self) -> UserDataBundle:
        with self.connect() as connection:
            profile_row = connection.execute("SELECT payload_json FROM user_profile WHERE profile_id = 1").fetchone()
            if profile_row is None:
                raise ValueError("No migrated user profile exists")
            account_data = json.loads(profile_row[0])
            inventory_state = connection.execute("SELECT * FROM inventory_state WHERE profile_id = 1").fetchone()
            club_rows = connection.execute("SELECT * FROM user_clubs ORDER BY rowid").fetchall()
            preference_data = json.loads(connection.execute("SELECT payload_json FROM user_preferences WHERE profile_id = 1").fetchone()[0])
            bag_rows = connection.execute("SELECT * FROM user_bags ORDER BY rowid").fetchall()
            observation_rows = connection.execute("SELECT payload_json FROM user_observations ORDER BY rowid").fetchall()
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
            entries = tuple(
                InventoryEntry(
                    club_id=row["club_id"], display_name=row["display_name"], unlocked=bool(row["unlocked"]),
                    current_level=row["current_level"], cards_owned=row["cards_owned"],
                    cards_required_for_next_upgrade=row["cards_required"], observed_at=row["observed_at"], source=row["source"],
                )
                for row in club_rows
            )
            inventory = Inventory(
                bool(inventory_state["inventory_complete"]), inventory_state["observed_at"], inventory_state["source"], entries
            )
            preferences = UserPreferences(
                priorities=tuple(
                    PreferenceItem(str(item["criterion"]), str(item["preference"]), item.get("weight"))
                    for item in preference_data.get("priorities", [])
                ),
                free_to_play_required=bool(preference_data.get("constraints", {}).get("free_to_play_required")),
                paid_special_balls_allowed=bool(preference_data.get("constraints", {}).get("paid_special_balls_allowed")),
            )
            saved_bags = []
            for row in bag_rows:
                club_ids = tuple(
                    item[0] for item in connection.execute(
                        "SELECT club_id FROM user_bag_clubs WHERE bag_id = ? ORDER BY position", (row["bag_id"],)
                    )
                )
                payload = json.loads(row["payload_json"])
                saved_bags.append(SavedBag(
                    row["bag_id"], row["name"], row["status"], club_ids,
                    tuple(json.loads(row["notes_json"])), _reference_profile(payload.get("reference")),
                ))
            observations = tuple(
                UserObservation(
                    identifier=str(item["id"]), status=str(item["status"]),
                    club_ids=tuple(str(value) for value in item.get("club_ids", [])), text=str(item["text"]),
                    unresolved_reference=item.get("unresolved_reference"),
                )
                for item in (json.loads(row[0]) for row in observation_rows)
            )
            return UserDataBundle(account, inventory, preferences, tuple(saved_bags), observations)

    def backup(self) -> Path:
        destination = self.path.parent / "backups" / (self.path.stem + "-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".sqlite")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
        return destination

    def inventory_documents(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM user_clubs ORDER BY display_name COLLATE NOCASE").fetchall()
            return [self._inventory_document(row) for row in rows]

    @staticmethod
    def _inventory_document(row: sqlite3.Row) -> dict[str, Any]:
        cards = row["cards_owned"]
        required = row["cards_required"]
        upgrade = None if cards is None or required is None else cards >= required
        return {
            "club_id": row["club_id"], "display_name": row["display_name"], "unlocked": bool(row["unlocked"]),
            "current_level": row["current_level"], "cards_owned": cards,
            "cards_required_for_next_upgrade": required, "upgrade_available": upgrade,
            "observed_at": row["observed_at"], "source": row["source"], "examined_at": row["examined_at"],
        }

    def apply_inventory_batch(self, changes: Sequence[Mapping[str, Any]], *, source: str = "guided_inventory_sync") -> Path:
        if not changes:
            raise ValueError("At least one inventory change is required")
        with self.connect() as connection:
            current_version = connection.execute("SELECT version_id FROM catalog_versions WHERE is_current = 1").fetchone()[0]
            official_ids = {row[0] for row in connection.execute("SELECT club_id FROM clubs WHERE version_id = ?", (current_version,))}
        for item in changes:
            if item.get("club_id") not in official_ids:
                raise ValueError(f"Unknown official club: {item.get('club_id')}")
            level, cards, required = item.get("current_level"), item.get("cards_owned"), item.get("cards_required_for_next_upgrade")
            if level is not None and (not isinstance(level, int) or level < 1):
                raise ValueError("Current level must be positive or unknown")
            if cards is not None and (not isinstance(cards, int) or cards < 0):
                raise ValueError("Cards owned must be non-negative or unknown")
            if required is not None and (not isinstance(required, int) or required < 1):
                raise ValueError("Upgrade threshold must be positive or unknown")
        backup = self.backup()
        timestamp = _now()
        with self.connect() as connection:
            for item in changes:
                before_row = connection.execute("SELECT * FROM user_clubs WHERE club_id = ?", (item["club_id"],)).fetchone()
                before = self._inventory_document(before_row) if before_row else None
                document = {
                    "club_id": item["club_id"], "display_name": item["display_name"],
                    "unlocked": bool(item.get("unlocked")), "current_level": item.get("current_level"),
                    "cards_owned": item.get("cards_owned"),
                    "cards_required_for_next_upgrade": item.get("cards_required_for_next_upgrade"),
                    "upgrade_available": None,
                    "observed_at": timestamp, "source": source,
                }
                connection.execute(
                    """INSERT INTO user_clubs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(club_id) DO UPDATE SET
                         display_name=excluded.display_name, unlocked=excluded.unlocked,
                         current_level=excluded.current_level, cards_owned=excluded.cards_owned,
                         cards_required=excluded.cards_required, observed_at=excluded.observed_at,
                         source=excluded.source, examined_at=excluded.examined_at, payload_json=excluded.payload_json""",
                    (
                        document["club_id"], document["display_name"], int(document["unlocked"]), document["current_level"],
                        document["cards_owned"], document["cards_required_for_next_upgrade"], timestamp, source, timestamp, _json(document),
                    ),
                )
                after_row = connection.execute("SELECT * FROM user_clubs WHERE club_id = ?", (item["club_id"],)).fetchone()
                connection.execute(
                    "INSERT INTO user_change_log(changed_at, entity_type, entity_id, action, before_json, after_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (timestamp, "inventory", item["club_id"], "synchronize", _json(before) if before else None, _json(self._inventory_document(after_row))),
                )
            connection.execute("UPDATE inventory_state SET observed_at = ?, source = ? WHERE profile_id = 1", (timestamp, source))
            connection.commit()
        return backup

    def bag_documents(self) -> list[dict[str, Any]]:
        bundle = self.load_user_bundle()
        return [
            {
                "id": bag.identifier, "name": bag.name, "status": bag.status,
                "club_ids": list(bag.club_ids), "notes": list(bag.notes),
                **({"reference": asdict(bag.reference)} if bag.reference else {}),
            }
            for bag in bundle.bags
        ]

    def save_bag(self, name: str, club_ids: Sequence[str], *, bag_id: str | None = None) -> tuple[Path, str]:
        if len(club_ids) != 5 or len(set(club_ids)) != 5:
            raise ValueError("Un sac doit contenir exactement cinq clubs différents.")
        backup = self.backup()
        timestamp = _now()
        with self.connect() as connection:
            owned = {row[0] for row in connection.execute("SELECT club_id FROM user_clubs WHERE unlocked = 1")}
            if any(item not in owned for item in club_ids):
                raise ValueError("Tous les clubs du sac doivent être marqués comme possédés.")
            reference = None
            notes = ["Sac enregistré dans SQLite."]
            status = "user_observed"
            if bag_id is None:
                base = re_slug(name)
                bag_id = base
                suffix = 2
                while connection.execute("SELECT 1 FROM user_bags WHERE bag_id = ?", (bag_id,)).fetchone():
                    bag_id = f"{base}_{suffix}"
                    suffix += 1
                before = None
            else:
                before_row = connection.execute(
                    "SELECT payload_json, status, notes_json FROM user_bags WHERE bag_id = ?", (bag_id,)
                ).fetchone()
                if before_row is None:
                    raise ValueError("Ce sac n'existe plus.")
                before = json.loads(before_row[0])
                reference = before.get("reference")
                status = before_row["status"]
                notes = list(json.loads(before_row["notes_json"]))
                connection.execute("DELETE FROM user_bag_clubs WHERE bag_id = ?", (bag_id,))
                connection.execute("DELETE FROM user_bags WHERE bag_id = ?", (bag_id,))
            document = {
                "id": bag_id, "name": name.strip(), "status": status,
                "club_ids": list(club_ids), "notes": notes,
                **({"reference": reference} if reference else {}),
            }
            connection.execute(
                "INSERT INTO user_bags VALUES (?, ?, ?, ?, ?, ?, ?)",
                (bag_id, name.strip(), status, _json(notes), timestamp, "guided_user_entry", _json(document)),
            )
            for position, club_id in enumerate(club_ids, start=1):
                connection.execute("INSERT INTO user_bag_clubs VALUES (?, ?, ?)", (bag_id, position, club_id))
            connection.execute("INSERT INTO user_change_log(changed_at, entity_type, entity_id, action, before_json, after_json) VALUES (?, ?, ?, ?, ?, ?)", (timestamp, "bag", bag_id, "update" if before else "create", _json(before) if before else None, _json(document)))
            connection.commit()
        return backup, bag_id

    def mark_bag_reference(self, bag_id: str, profile: BagReferenceProfile) -> Path:
        if profile.role not in {"stable", "experimental"}:
            raise ValueError("Le rôle de référence doit être stable ou expérimental.")
        backup = self.backup()
        timestamp = _now()
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM user_bags WHERE bag_id = ?", (bag_id,)).fetchone()
            if row is None:
                raise ValueError("Ce sac n'existe plus.")
            clubs = {
                item[0] for item in connection.execute(
                    "SELECT club_id FROM user_bag_clubs WHERE bag_id = ?", (bag_id,)
                )
            }
            if profile.primary_club_id and profile.primary_club_id not in clubs:
                raise ValueError("Le club principal doit appartenir au sac.")
            if profile.club_notes and not set(profile.club_notes).issubset(clubs):
                raise ValueError("Une note de club ne peut viser qu'un club du sac.")
            before = json.loads(row["payload_json"])
            after = {**before, "status": "user_reference", "reference": asdict(profile)}
            connection.execute(
                "UPDATE user_bags SET status = ?, observed_at = ?, source = ?, payload_json = ? WHERE bag_id = ?",
                ("user_reference", timestamp, "user_reference_metadata", _json(after), bag_id),
            )
            connection.execute(
                "INSERT INTO user_change_log(changed_at, entity_type, entity_id, action, before_json, after_json) VALUES (?, ?, ?, ?, ?, ?)",
                (timestamp, "bag", bag_id, "mark_reference", _json(before), _json(after)),
            )
            connection.commit()
        return backup

    def replace_reference_bag(
        self, bag_id: str, club_ids: Sequence[str], *, confirmed: bool = False,
    ) -> tuple[Path, str]:
        if not confirmed:
            raise ValueError("Le remplacement d'un sac de référence exige une confirmation explicite.")
        bag = next((item for item in self.load_user_bundle().bags if item.identifier == bag_id), None)
        if bag is None or bag.reference is None:
            raise ValueError("Le sac sélectionné n'est pas une référence utilisateur.")
        return self.save_bag(bag.name, club_ids, bag_id=bag_id)

    def delete_bag(self, bag_id: str) -> Path:
        backup = self.backup()
        with self.connect() as connection:
            row = connection.execute("SELECT payload_json FROM user_bags WHERE bag_id = ?", (bag_id,)).fetchone()
            if row is None:
                raise ValueError("Ce sac n'existe plus.")
            connection.execute("DELETE FROM user_bags WHERE bag_id = ?", (bag_id,))
            connection.execute("INSERT INTO user_change_log(changed_at, entity_type, entity_id, action, before_json, after_json) VALUES (?, ?, ?, ?, ?, ?)", (_now(), "bag", bag_id, "delete", row[0], None))
            connection.commit()
        return backup

    def export_user_json(self, output_dir: str | Path) -> tuple[Path, ...]:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            account = json.loads(connection.execute("SELECT payload_json FROM user_profile WHERE profile_id = 1").fetchone()[0])
            state = connection.execute("SELECT * FROM inventory_state WHERE profile_id = 1").fetchone()
            preferences = json.loads(connection.execute("SELECT payload_json FROM user_preferences WHERE profile_id = 1").fetchone()[0])
            observations = [json.loads(row[0]) for row in connection.execute("SELECT payload_json FROM user_observations ORDER BY rowid")]
        documents = {
            "account.json": account,
            "inventory.json": {"schema_version": "1.0.0", "inventory_complete": bool(state["inventory_complete"]), "observed_at": state["observed_at"], "source": "sqlite_export", "entries": self.inventory_documents()},
            "preferences.json": preferences,
            "bags.json": {"schema_version": "1.0.0", "observed_at": _now(), "source": "sqlite_export", "bags": self.bag_documents()},
            "observations.json": {"schema_version": "1.0.0", "observed_at": _now(), "source": "sqlite_export", "observations": observations},
        }
        paths = []
        for name, document in documents.items():
            path = destination / name
            path.write_text(_pretty(document), encoding="utf-8", newline="\n")
            paths.append(path)
        return tuple(paths)


def re_slug(value: str) -> str:
    result = "".join(character.casefold() if character.isalnum() else "_" for character in value.strip())
    return "_".join(part for part in result.split("_") if part) or "mon_sac"
