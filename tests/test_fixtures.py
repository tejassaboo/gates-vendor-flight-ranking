"""The environment: the vendored copies stay identical, the handbook is the task's instructions, the
generator reproduces the committed fixtures, the fixtures hold their invariants (recomputed here with
zoneinfo, which the plugin itself never uses at evaluation time), and every fact the answer depends on is
a structured field."""

import json
from datetime import datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

import pytest
from helpers import DATA, ROOT, SCENARIOS

from contract import TripRequestOutput
from plugin.fixtures import world
from plugin.rules import hotel_problems, oracle
from plugin.tools_dev.generate import build
from plugin.world import schema_problems

SCENARIO_KEYS = [
    "scenario",
    "request_text",
    "booking_date",
    "traveler_id",
    "origin",
    "destination",
    "departure_date",
    "preferred_departure_local",
]


@pytest.mark.parametrize("module", ["rules.py", "world.py"])
def test_the_verifier_runs_the_same_code(module: str) -> None:
    assert (ROOT / "verifier" / module).read_bytes() == (ROOT / "src" / "plugin" / module).read_bytes()


def test_the_shared_core_is_vendored_unchanged() -> None:
    shared = ROOT.parent / "_shared_core"
    if not shared.is_dir():
        pytest.skip("the shared core lives next to the plugin only in the development tree")
    assert (ROOT / "src" / "plugin" / "world.py").read_bytes() == (shared / "world.py").read_bytes()
    assert (ROOT / "src" / "plugin" / "tools_dev" / "worldgen.py").read_bytes() == (shared / "worldgen.py").read_bytes()


def instructions(manifest_text):
    """The rank-gates-vendor-trip task's instructions: the `|-` block scalar under it, unindented."""
    lines = manifest_text.split("\n")
    start = lines.index("    instructions: |-") + 1
    block = []
    for line in lines[start:]:
        if line and not line.startswith("      "):
            break
        block.append(line[6:])
    return "\n".join(block).rstrip("\n")


def test_the_handbook_is_the_task_instructions() -> None:
    handbook = (DATA / "handbook.md").read_text(encoding="utf-8")
    assert instructions((ROOT / "nanoagent.yaml").read_text(encoding="utf-8")) == handbook.rstrip("\n")
    assert len(handbook.split()) <= 1500


def test_the_handbook_pins_its_source_and_states_the_toy_rules() -> None:
    handbook = (DATA / "handbook.md").read_text(encoding="utf-8")
    for needle in (
        "travel%20and%20expense%20-%20vendor.pdf",
        "Effective 7/1/2024",
        "2026-11-02",
        "## Clarifications (toy rules)",
        "## Rules not in scope",
        "three keys in all",
        "Seattle uses 30000",
        "earlier than 05:00",
        "same segment",
        "## Step plan",
    ):
        assert needle in handbook, needle


def test_the_generator_reproduces_the_committed_fixtures() -> None:
    files = build()
    assert sorted(files) == sorted(path.relative_to(DATA).as_posix() for path in DATA.rglob("*.json"))
    for relative, text in files.items():
        assert (DATA / relative).read_text(encoding="utf-8") == text, relative


def test_the_fixtures_follow_the_schema() -> None:
    assert schema_problems(world()) == []
    assert hotel_problems(world()) == []


def local(stamp, timezone):
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo(timezone))


def utc(stamp):
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%MZ").replace(tzinfo=ZoneInfo("UTC"))


def test_segment_times_are_consistent() -> None:
    airports = world()["airports"]
    for segment in world()["segments"].values():
        depart = local(segment["depart_local"], airports[segment["origin"]]["timezone"])
        arrive = local(segment["arrive_local"], airports[segment["destination"]]["timezone"])
        assert depart == utc(segment["depart_utc"]) and arrive == utc(segment["arrive_utc"]), segment["segment_id"]
        assert (arrive - depart).total_seconds() == segment["in_air_minutes"] * 60


def test_itinerary_totals_and_fares() -> None:
    data = world()
    for record in data["itineraries"].values():
        segments = [data["segments"][segment_id] for segment_id in record["segment_ids"]]
        layovers = [int((utc(b["depart_utc"]) - utc(a["arrive_utc"])).total_seconds() // 60) for a, b in pairwise(segments)]
        assert record["layover_minutes"] == layovers and record["connections"] == len(segments) - 1
        assert record["total_in_air_minutes"] == sum(segment["in_air_minutes"] for segment in segments)
        assert record["longest_segment_minutes"] == max(segment["in_air_minutes"] for segment in segments)
        assert record["total_elapsed_minutes"] == int((utc(segments[-1]["arrive_utc"]) - utc(segments[0]["depart_utc"])).total_seconds() // 60)
        international = not data["airports"][segments[-1]["destination"]]["continental_us"]
        sold = [cabin for cabin, fare in record["fares_cents"].items() if fare is not None]
        assert "economy" in sold and (not international or {"premium_economy", "business"} <= set(sold)), record["itinerary_id"]
        assert all(isinstance(fare, int) and fare > 0 for fare in record["fares_cents"].values() if fare is not None)


def test_every_flight_is_flown_by_its_seller() -> None:
    # No code-shares: the marketing carrier that decides "preferred" is also the operating carrier.
    assert all(segment["marketing_carrier"] == segment["operating_carrier"] for segment in world()["segments"].values())


def test_no_trip_date_crosses_a_daylight_saving_change() -> None:
    # Departure-time distance compares wall-clock times at one airport; no scenario date sits on a DST switch.
    for scenario in SCENARIOS:
        facts = json.loads((DATA / "scenarios" / f"{scenario}.json").read_text(encoding="utf-8"))
        timezone = ZoneInfo(world()["airports"][facts["origin"]]["timezone"])
        day = datetime.strptime(facts["departure_date"], "%Y-%m-%d")
        offsets = {day.replace(hour=hour, tzinfo=timezone).utcoffset() for hour in range(24)}
        assert len(offsets) == 1, scenario


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_scenario_files_hold_facts_only(scenario: str) -> None:
    facts = json.loads((DATA / "scenarios" / f"{scenario}.json").read_text(encoding="utf-8"))
    assert list(facts) == SCENARIO_KEYS and facts["scenario"] == scenario  # no expected answer anywhere
    assert facts["traveler_id"] in world()["travelers"]
    assert facts["origin"] in world()["airports"] and facts["destination"] in world()["airports"]
    assert facts["preferred_departure_local"][:10] == facts["departure_date"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_policy_fact_is_a_structured_field(scenario: str) -> None:
    # The oracle needs only these scenario fields (plus the fixtures), and each reaches the agent as a typed
    # field of get_trip_request; request_text is flavour, and the oracle runs without it.
    used = ["origin", "destination", "departure_date", "preferred_departure_local"]
    assert set(used) <= set(TripRequestOutput.__dataclass_fields__)
    facts = json.loads((DATA / "scenarios" / f"{scenario}.json").read_text(encoding="utf-8"))
    bare = {"scenario": scenario, **{key: facts[key] for key in used}}
    assert oracle(world(), bare) == oracle(world(), facts)


def test_gitignore_keeps_the_bundled_data() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    assert not any(pattern in ("*.json", "*.md", "data/", "src/") for pattern in ignored)
