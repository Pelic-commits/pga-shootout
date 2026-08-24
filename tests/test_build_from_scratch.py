from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from pga_shootout.strategy_optimizer import (
    BuildFromScratchRequest,
    StrategyOptimizationError,
    StrategyOptimizationRequest,
    StrategyOptimizer,
)


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pga_shootout.sqlite"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
REGISTRY = ROOT / "data" / "strategies" / "strategies.json"


def _optimizer(database: Path, catalog: Path = CATALOG) -> StrategyOptimizer:
    return StrategyOptimizer(
        user_data_path=database,
        catalog_path=catalog,
        strategy_registry_path=REGISTRY,
    )


def _request(primary: str = "high_flight") -> BuildFromScratchRequest:
    return BuildFromScratchRequest("par3", primary, limit=3, max_evaluations=200)


def _signature(result) -> tuple[tuple[str, ...], ...]:
    return tuple(item.composition for item in result.retained_results)


def test_public_contract_cannot_express_a_saved_bag_seed(tmp_path):
    database = tmp_path / "user.sqlite"
    shutil.copy2(DATABASE, database)
    result = _optimizer(database).build_from_scratch(_request())

    assert result.retained_results
    assert result.search.saved_bag_candidates_injected == 0
    assert result.search.known_candidates_injected == 0
    assert {item.origin for item in result.retained_results} == {"build_from_scratch"}
    assert all("high_flight" in item.composition for item in result.retained_results)

    with pytest.raises(StrategyOptimizationError, match="ni sac de référence"):
        _optimizer(database).optimize(StrategyOptimizationRequest(
            "par3", search_mode="build_from_scratch", target_bag_id="par3_divebomb",
            club_roles={"high_flight": "auto"}, max_evaluations=10,
        ))


def test_saved_bags_have_no_effect_and_empty_saved_bag_table_is_supported(tmp_path):
    with_bags = tmp_path / "with.sqlite"
    without_bags = tmp_path / "without.sqlite"
    shutil.copy2(DATABASE, with_bags)
    shutil.copy2(DATABASE, without_bags)
    with sqlite3.connect(without_bags) as connection:
        connection.execute("DELETE FROM user_bag_clubs")
        connection.execute("DELETE FROM user_bags")

    expected = _signature(_optimizer(with_bags).build_from_scratch(_request()))
    actual = _signature(_optimizer(without_bags).build_from_scratch(_request()))
    assert actual == expected


def test_renaming_club_data_does_not_change_candidate_identity(tmp_path):
    database = tmp_path / "user.sqlite"
    catalog = tmp_path / "clubs_official.json"
    shutil.copy2(DATABASE, database)
    document = json.loads(CATALOG.read_text(encoding="utf-8"))
    document["clubs"]["high_flight"]["name"] = "RENAMED WITHOUT SEMANTIC CHANGE"
    catalog.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(CATALOG.with_name("semantic_map.json"), catalog.with_name("semantic_map.json"))

    original = _signature(_optimizer(database).build_from_scratch(_request()))
    renamed = _signature(_optimizer(database, catalog).build_from_scratch(_request()))
    assert renamed == original


def test_new_data_only_club_is_immediately_usable_without_business_code(tmp_path):
    database = tmp_path / "user.sqlite"
    catalog = tmp_path / "clubs_official.json"
    shutil.copy2(DATABASE, database)
    document = json.loads(CATALOG.read_text(encoding="utf-8"))
    source = deepcopy(document["clubs"]["high_flight"])
    source["id"] = "synthetic_tomorrow"
    source["name"] = "Synthetic Tomorrow Club"
    for ability in source["abilities"]:
        ability["occurrence_id"] = ability["occurrence_id"].replace(
            "high_flight", "synthetic_tomorrow", 1,
        )
    document["clubs"]["synthetic_tomorrow"] = source
    catalog.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(CATALOG.with_name("semantic_map.json"), catalog.with_name("semantic_map.json"))
    with sqlite3.connect(database) as connection:
        connection.execute(
            """INSERT INTO user_clubs
               SELECT ?, ?, unlocked, current_level, cards_owned, cards_required,
                      observed_at, source, examined_at, payload_json
               FROM user_clubs WHERE club_id = ?""",
            ("synthetic_tomorrow", "Synthetic Tomorrow Club", "high_flight"),
        )

    result = _optimizer(database, catalog).build_from_scratch(BuildFromScratchRequest(
        "par3", "synthetic_tomorrow", club_roles={"synthetic_tomorrow": "attack"},
        limit=3, max_evaluations=300,
    ))
    assert result.retained_results
    assert all("synthetic_tomorrow" in item.composition for item in result.retained_results)
    assert all(
        club.role != "neutral" or club.club_id == "synthetic_tomorrow"
        or any(step.unresolved_abilities for step in club.steps)
        for item in result.retained_results for club in item.clubs
    )


def test_allowed_brands_reject_an_explicit_primary_club_outside_filter(tmp_path):
    database = tmp_path / "user.sqlite"
    shutil.copy2(DATABASE, database)
    with pytest.raises(StrategyOptimizationError, match="marques autorisées"):
        _optimizer(database).build_from_scratch(BuildFromScratchRequest(
            "par3", "high_flight", allowed_brands=("phoenix",), max_evaluations=10,
        ))
