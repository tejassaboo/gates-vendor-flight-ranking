"""The verifier against hand-written submissions (no agent). Correct, incorrect, missing, consistency
and verifier-caught malformed cases run through verify_task; shape
problems are refused by build_output before any verifier runs, exactly as in NanoAgent."""

import json

import pytest
from helpers import SCENARIOS, TASK, arguments, case, reference, verdict
from slimconfig import build_output

import verifier
from contract import GatesBookingOutput, HotelsInput, SearchInput

ORDER = [
    "reference-matches-oracle",
    "ranked-ids-exist",
    "ranked-ids-serve-trip",
    "hotel-exists",
    "hotel-in-destination",
    "ranked-unique",
    "ranked-complete",
    "selected-is-first",
    "selected-correct",
    "ranking-correct",
    "cabin-correct",
    "hotel-not-banned",
    "hotel-within-cap",
    "hotel-correct",
]
BOSTON = case("boston-board-retreat")["expected"]
REASONS = sorted({broken["reason"] for scenario in SCENARIOS for broken in case(scenario)["broken"]})


RANKED = BOSTON["ranked_itinerary_ids"]  # I973, I467, I278, I552, I812, I283, I316, I595


def test_the_cases_exercise_every_submission_reason_code() -> None:
    # reference-matches-oracle needs a broken answer key, not a broken submission: tested below.
    assert REASONS == sorted(set(ORDER) - {"reference-matches-oracle"})


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_hand_written_answer_passes(scenario: str) -> None:
    result = verdict(scenario, case(scenario)["expected"])
    assert result["valid"] is True and result["score"] == 1.0, result["message"]
    assert [entry["id"] for entry in result["details"]["constraints"]] == ORDER
    assert all(entry["ok"] is True for entry in result["details"]["constraints"])


@pytest.mark.parametrize(
    ("scenario", "index"), [(scenario, index) for scenario in SCENARIOS for index in range(len(case(scenario)["broken"]))]
)
def test_each_broken_answer_fails_with_its_reason_code(scenario: str, index: int) -> None:
    broken = case(scenario)["broken"][index]
    result = verdict(scenario, {**case(scenario)["expected"], **broken["change"]})
    assert result["valid"] is False and 0.0 <= result["score"] < 1.0
    assert result["message"].split(":")[0] == broken["reason"], (broken["why"], result["message"])
    failing = [entry for entry in result["details"]["constraints"] if entry["ok"] is False]
    assert failing[0]["id"] == broken["reason"]
    assert all({"id", "constraint", "ok", "expected", "actual", "message"} == set(entry) for entry in failing)


@pytest.mark.parametrize(
    ("scenario", "change", "needle"),
    [
        ("boston-board-retreat", {"allowed_cabin": "business"}, "NS 902 departs 21:00 (not after 21:00 nor before 05:00), 331 min > 300"),
        ("mexico-city-lab-audit", {"allowed_cabin": "business"}, "CW 1260 300 min not > 300"),
        ("seattle-headquarters-visit", {"allowed_cabin": "premium_economy"}, "CW 2 departs 00:30 (in the late window), 345 min > 300"),
        ("miami-vector-lab-demo", {"allowed_cabin": "business"}, "CW 2210 departs 21:30 (in the late window), 55 min not > 300"),
        ("london-global-health-convening", {"hotel_id": "H451"}, "costs 47501 cents before tax, 1 over London's cap of 47500"),
        ("toronto-immunization-forum", {"hotel_id": "H927"}, "costs 30001 cents before tax, 1 over Toronto's cap of 30000"),
        ("washington-policy-roundtable", {"ranked_itinerary_ids": ["I806", "I702", "I188", "I489", "I836", "I907", "I774"], "selected_itinerary_id": "I806"}, "itinerary_id I702 < I806"),
        ("boston-board-retreat", {"ranked_itinerary_ids": ["I973", "I278", "I467", "I552", "I812", "I283", "I316", "I595"]}, "I467 departs 21:01, 29 min from the preferred 21:30; I278 departs 20:55, 35 min"),
        ("nashville-education-summit", {"ranked_itinerary_ids": ["I837", "I913", "I565", "I487", "I271", "I332"], "selected_itinerary_id": "I837"}, "key 1 (nonstop): I271 is nonstop, I837 has 1 connection(s)"),
        ("nairobi-field-mission", {"ranked_itinerary_ids": ["I995", "I577", "I164", "I671", "I308", "I235"], "selected_itinerary_id": "I995"}, "uses GP"),
        ("honolulu-health-workshop", {"hotel_id": "H378"}, "is H350 (Kaimana Reef Hotel) at 27200 cents, not H378 at 28400; taxes never count"),
        ("tampa-grantee-expo", {"hotel_id": "H198"}, "Tampa Marriott Water Street is named on the non-reimbursable list"),
        ("boston-board-retreat", {"hotel_id": "H336"}, "The Charles Hotel is named on the non-reimbursable list"),
        ("los-angeles-media-screening", {"allowed_cabin": "premium_economy"}, "CW 71 departs 04:59 (in the late window), 335 min > 300"),
        ("los-angeles-media-screening", {"hotel_id": "H781"}, "is H394 (Westwood Palm Court) at 27400 cents, not H781 at 27400"),
        ("toronto-immunization-forum", {"allowed_cabin": "economy"}, "international: business needs one flight > 300 min, else economy; NS 70 320 min > 300; NS 440 270 min not > 300"),
        ("denver-sanitation-forum", {"allowed_cabin": "business"}, "CW 1500 departs 21:05 (in the late window), 300 min not > 300"),
    ],
)
def test_messages_name_the_rule_and_the_numbers(scenario: str, change: dict, needle: str) -> None:
    message = verdict(scenario, {**case(scenario)["expected"], **change})["message"]
    assert needle in message, message


def test_a_failed_stage_leaves_later_stages_unchecked() -> None:
    result = verdict("boston-board-retreat", {**BOSTON, "hotel_id": "H999"})
    states = {entry["id"]: entry["ok"] for entry in result["details"]["constraints"]}
    assert states["hotel-exists"] is False and states["hotel-in-destination"] is True  # skipped, not crashed
    assert all(states[identifier] is None for identifier in ORDER[5:])


def test_a_message_counts_the_other_failures() -> None:
    wrong = {**BOSTON, "allowed_cabin": "business", "hotel_id": "H290"}  # the Four Seasons Boston: banned, and not cheapest
    result = verdict("boston-board-retreat", wrong)
    assert result["message"].startswith("cabin-correct:") and result["message"].endswith("(+2 more)")


def test_a_wrong_answer_key_is_caught_before_the_submission() -> None:
    wrong_key = build_output({**BOSTON, "allowed_cabin": "business"}, GatesBookingOutput)
    result = verifier.verify_task(TASK, arguments("boston-board-retreat"), build_output(BOSTON, GatesBookingOutput), wrong_key, ".")
    assert result["valid"] is False and result["message"].startswith("reference-matches-oracle")


def test_without_a_pinned_reference_the_oracle_still_decides() -> None:
    assert verdict("boston-board-retreat", BOSTON, pinned=False)["valid"] is True
    assert verdict("boston-board-retreat", {**BOSTON, "allowed_cabin": "business"}, pinned=False)["valid"] is False


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"ranked_itinerary_ids": []}, "ranked-complete"),  # missing: an empty list where every candidate is required
        ({"ranked_itinerary_ids": RANKED[:-1]}, "ranked-complete"),
        ({"selected_itinerary_id": "I467"}, "selected-is-first"),
        ({"selected_itinerary_id": "I000"}, "ranked-ids-exist"),
        ({"hotel_id": "H265"}, "hotel-in-destination"),  # a New York hotel on a Boston trip
        ({"hotel_id": ""}, "hotel-exists"),
        ({"ranked_itinerary_ids": [*RANKED, "I973"]}, "ranked-unique"),
        ({"ranked_itinerary_ids": [*RANKED[:-2], RANKED[-1], RANKED[-2]]}, "ranking-correct"),  # last pair swapped
    ],
)
def test_incorrect_missing_and_inconsistent_answers(change: dict, reason: str) -> None:
    result = verdict("boston-board-retreat", {**BOSTON, **change})
    assert result["valid"] is False and result["message"].split(":")[0] == reason, result["message"]


@pytest.mark.parametrize(
    "raw",
    [
        {**BOSTON, "allowed_cabin": "Business"},  # wrong case
        {**BOSTON, "allowed_cabin": "first"},  # first class is never an allowed cabin
        {**BOSTON, "allowed_cabin": None},  # null for a non-optional field
        {**BOSTON, "ranked_itinerary_ids": "I973,I467"},  # a string, not a list
        {**BOSTON, "ranked_itinerary_ids": ["I973", 467]},  # an id as a number
        {**BOSTON, "hotel_id": 271},
        {key: value for key, value in BOSTON.items() if key != "hotel_id"},  # missing field
        {**BOSTON, "rationale": "cheapest"},  # extra field
        ["I973", "premium_economy"],  # not an object
    ],
)
def test_malformed_outputs_are_refused_before_the_verifier(raw) -> None:
    with pytest.raises(ValueError):
        build_output(raw, GatesBookingOutput)


def test_non_json_output_never_parses() -> None:
    with pytest.raises(json.JSONDecodeError):
        json.loads("{ranked_itinerary_ids: [I973]}")


@pytest.mark.parametrize(
    ("arguments_value", "output_value"),
    [(None, None), ("nonsense", 7), (arguments("boston-board-retreat"), None), (arguments("boston-board-retreat"), {"hotel_id": "H271"})],
)
def test_the_verifier_never_raises(arguments_value, output_value) -> None:
    result = verifier.verify_task(TASK, arguments_value, output_value, None, ".")
    assert result["valid"] is False and result["message"].startswith("verifier-error")


def test_an_unknown_task_or_tool_id_is_a_failed_verdict_not_an_exception() -> None:
    gold = build_output(BOSTON, GatesBookingOutput)
    for result in (
        verifier.verify_task("book-trip", arguments("boston-board-retreat"), gold, None, "."),
        verifier.verify_task(None, arguments("boston-board-retreat"), gold, None, "."),
        verifier.verify_input("search_flights", None),
        verifier.verify_output("search_flights", None, None, "."),
    ):
        assert result["valid"] is False and result["message"].startswith("verifier-error"), result


def test_an_unknown_scenario_or_garbage_reference_is_a_failed_verdict() -> None:
    gold = build_output(BOSTON, GatesBookingOutput)
    unknown = verifier.verify_task(TASK, {"scenario": "atlantis-summit"}, gold, None, ".")
    assert unknown["valid"] is False and unknown["message"].startswith("verifier-error")
    garbage = verifier.verify_task(TASK, arguments("boston-board-retreat"), gold, "not a booking", ".")
    assert garbage["valid"] is False and garbage["message"].startswith("reference-matches-oracle")


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        # The selected id exists and is ranked nowhere: another trip's itinerary heads nothing.
        ({"selected_itinerary_id": "I115"}, "selected-is-first"),
        # A candidate is replaced by another trip's itinerary of the same inventory.
        ({"ranked_itinerary_ids": [*RANKED[:-1], "I115"]}, "ranked-ids-serve-trip"),
        # The right set in reverse: the full order must match, not just the head.
        ({"ranked_itinerary_ids": [RANKED[0], *reversed(RANKED[1:])]}, "ranking-correct"),
    ],
)
def test_ids_from_other_trips_and_reordered_tails_are_caught(change: dict, reason: str) -> None:
    result = verdict("boston-board-retreat", {**BOSTON, **change})
    assert result["valid"] is False and result["message"].split(":")[0] == reason, result["message"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_verdicts_are_deterministic_plain_json(scenario: str) -> None:
    broken = {**case(scenario)["expected"], **case(scenario)["broken"][0]["change"]}
    for output in (case(scenario)["expected"], broken):
        first, second = verdict(scenario, output), verdict(scenario, output)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)  # no default=: plain JSON only
        assert isinstance(first["score"], float) and 0.0 <= first["score"] <= 1.0


@pytest.mark.parametrize(
    ("raw", "valid"),
    [
        ({"origin": "SEA", "destination": "BOS", "date": "2026-12-07"}, True),
        ({"origin": "SEA", "destination": "SEA", "date": "2026-12-07"}, False),
        ({"origin": "sea", "destination": "BOS", "date": "2026-12-07"}, False),
        ({"origin": "ZZZ", "destination": "BOS", "date": "2026-12-07"}, False),  # well-formed, not in the inventory
        ({"origin": "SEA", "destination": "BOS", "date": "2026-02-30"}, False),
    ],
)
def test_search_input_checks(raw: dict, valid: bool) -> None:
    assert verifier.verify_input("search_itineraries", build_output(raw, SearchInput))["valid"] is valid


@pytest.mark.parametrize(("city", "valid"), [("Boston", True), ("  ", False)])
def test_hotels_input_checks(city: str, valid: bool) -> None:
    assert verifier.verify_input("get_hotels", build_output({"city": city}, HotelsInput))["valid"] is valid


def test_the_reference_tool_output_is_checked_against_the_oracle() -> None:
    good = verifier.verify_output("compute_travel_desk_booking", arguments("tampa-grantee-expo"), reference("tampa-grantee-expo"), ".")
    bad = verifier.verify_output("compute_travel_desk_booking", arguments("tampa-grantee-expo"), reference("miami-vector-lab-demo"), ".")
    assert good["valid"] is True and bad["valid"] is False


# ---- partial credit: valid stays strict, score says how much is right ---------------------------------


def score_of(scenario, change):
    return verdict(scenario, {**case(scenario)["expected"], **change})["score"]


def test_a_valid_answer_scores_exactly_one_and_a_wrong_one_less() -> None:
    for scenario in SCENARIOS:
        assert verdict(scenario, case(scenario)["expected"])["score"] == 1.0
        for broken in case(scenario)["broken"]:
            result = verdict(scenario, {**case(scenario)["expected"], **broken["change"]})
            assert result["valid"] is False and result["score"] < 1.0, broken["why"]


@pytest.mark.parametrize(
    ("change", "score"),
    [
        ({"ranked_itinerary_ids": [*RANKED[:-2], RANKED[-1], RANKED[-2]]}, 0.92),  # 6 of 8 positions: 30 * 6 // 8 = 22
        ({"allowed_cabin": "business"}, 0.8),  # too high
        ({"allowed_cabin": "economy"}, 0.8),  # too low: the same loss
        ({"hotel_id": "H290"}, 0.8),  # banned
        ({"hotel_id": "H906"}, 0.8),  # over the cap: the same loss
        ({"hotel_id": "H752"}, 0.8),  # compliant but not the cheapest
        ({"allowed_cabin": "business", "hotel_id": "H290"}, 0.6),
        ({"ranked_itinerary_ids": [RANKED[1], RANKED[0], *RANKED[2:]], "selected_itinerary_id": RANKED[1]}, 0.42),  # 6 of 8 positions
        ({"ranked_itinerary_ids": [RANKED[1], RANKED[0], *RANKED[2:]]}, 0.42),  # selected is right but not first: G8
        ({"ranked_itinerary_ids": [RANKED[0], *reversed(RANKED[1:])]}, 0.77),  # first and middle hold: 30 * 2 // 8 = 7
        ({"ranked_itinerary_ids": RANKED[:-1]}, 0.7),  # incomplete: no order share at all
        ({"ranked_itinerary_ids": [*RANKED, "I973"]}, 0.7),  # a repeat: no order share
        ({"ranked_itinerary_ids": [RANKED[0]]}, 0.7),  # the lazy one-id ranking
        ({"ranked_itinerary_ids": [*RANKED, "I000"]}, 0.5),  # a stray id: capped
        ({"ranked_itinerary_ids": [*RANKED[:-1], "I115"]}, 0.5),  # another trip's id: capped
        ({"hotel_id": "H999"}, 0.5),  # unknown hotel: 0.8 capped at 0.5
        ({"hotel_id": "H265"}, 0.5),  # a hotel in another city: capped
    ],
)
def test_partial_scores(change: dict, score: float) -> None:
    assert score_of("boston-board-retreat", change) == score


def test_a_right_cabin_on_the_wrong_flight_earns_nothing() -> None:
    # The cabin is defined on the selected itinerary: with the wrong selection it is a coincidence.
    swapped = {"ranked_itinerary_ids": [RANKED[1], RANKED[0], *RANKED[2:]], "selected_itinerary_id": RANKED[1]}
    with_cabin = verdict("boston-board-retreat", {**BOSTON, **swapped})
    without = verdict("boston-board-retreat", {**BOSTON, **swapped, "allowed_cabin": "business"})
    assert with_cabin["score"] == without["score"] == 0.42
    assert with_cabin["details"]["score_parts"] == {"selection": 0.0, "order": 0.22, "cabin": 0.0, "hotel": 0.2, "integrity_cap": None}


def test_lazy_and_other_scenario_answers_score_near_zero() -> None:
    empty = {"ranked_itinerary_ids": [], "selected_itinerary_id": "", "allowed_cabin": "economy", "hotel_id": ""}
    for scenario in SCENARIOS:
        assert verdict(scenario, empty)["score"] == 0.0
        for other in SCENARIOS:
            if other != scenario and case(other)["expected"] != case(scenario)["expected"]:
                result = verdict(scenario, case(other)["expected"])
                assert result["valid"] is False and result["score"] <= 0.2, (scenario, other, result["score"])
    # The two Mexico City trips share a city and so a hotel: another trip's answer earns the hotel share only.
    assert verdict("mexico-city-lab-audit", case("mexico-city-nutrition-summit")["expected"])["score"] == 0.2
    assert verdict("boston-board-retreat", case("new-york-donor-briefing")["expected"])["score"] == 0.0


def test_scores_are_symmetric_at_the_boundaries() -> None:
    # Denver: 21:05 and exactly 300 min, premium_economy. Business (too high) and economy (too low) lose the same share.
    assert score_of("denver-sanitation-forum", {"allowed_cabin": "business"}) == score_of("denver-sanitation-forum", {"allowed_cabin": "economy"}) == 0.8
    # Toronto: the hotel one cent over the cap and the banned one that is cheaper lose the same share.
    assert score_of("toronto-immunization-forum", {"hotel_id": "H927"}) == score_of("toronto-immunization-forum", {"hotel_id": "H376"}) == 0.8


def test_a_broken_answer_key_scores_zero_whatever_the_submission() -> None:
    wrong_key = build_output({**BOSTON, "allowed_cabin": "business"}, GatesBookingOutput)
    result = verifier.verify_task(TASK, arguments("boston-board-retreat"), build_output(BOSTON, GatesBookingOutput), wrong_key, ".")
    assert result["valid"] is False and result["score"] == 0.0 and result["details"]["score_parts"] is None
