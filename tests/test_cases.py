"""Every scenario end to end without an LLM: the oracle equals the hand-written expectation, the answer
is unique, the answer does not depend on request_text, and a scripted agent written from the handbook
alone reaches it through the tools within the step budget; each broken variant of its answer fails with
the case's reason code."""

from itertools import pairwise

import pytest
from helpers import ROOT, SCENARIOS, case, verdict
from scripted_agent import run
from slimconfig import build_output, plain_output

from contract import TOOLS, GatesBookingOutput, Tool
from plugin import get_hotels, get_trip_request, search_itineraries
from plugin.fixtures import scenario as load_scenario
from plugin.fixtures import world
from plugin.rules import candidates, compliant_hotels, oracle, rank_key

IMPLEMENTATIONS = {
    Tool.GET_TRIP_REQUEST: get_trip_request,
    Tool.SEARCH_ITINERARIES: search_itineraries,
    Tool.GET_HOTELS: get_hotels,
}
MAX_TOOL_CALLS = 4  # plus submit, within the hosted 6 steps whose last may not call tools
# The one scenario whose ranking needs the last tie-break (itinerary_id): every other key ties.
ID_TIEBREAKS = {"washington-policy-roundtable": [("I115", "I852")]}


def call(tool, arguments):
    """A tool call as NanoAgent makes it: plain JSON in, built into the input class, plain JSON out."""
    given, made = TOOLS[Tool(tool)]
    output = IMPLEMENTATIONS[Tool(tool)](build_output(arguments, given))
    assert isinstance(output, made)
    return plain_output(output)


def test_every_scenario_has_a_case() -> None:
    assert sorted(SCENARIOS) == sorted(path.stem for path in (ROOT / "tests" / "cases").glob("*.json"))


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_oracle_equals_the_hand_written_expectation(scenario: str) -> None:
    assert oracle(world(), load_scenario(scenario)) == case(scenario)["expected"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_answer_is_unique(scenario: str) -> None:
    facts = load_scenario(scenario)
    keys = sorted(rank_key(world(), facts, item) for item in candidates(world(), facts))
    # A strict total order; the itinerary_id tie-break is needed only where the case documents it.
    needed = [(first[4], second[4]) for first, second in pairwise(keys) if first[:4] == second[:4]]
    assert needed == ID_TIEBREAKS.get(scenario, [])
    hotels = compliant_hotels(world(), facts)
    assert len(hotels) == 1 or hotels[0]["rate_before_tax_cents"] < hotels[1]["rate_before_tax_cents"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_answer_never_depends_on_request_text(scenario: str) -> None:
    facts = load_scenario(scenario)
    assert oracle(world(), {**facts, "request_text": ""}) == oracle(world(), facts)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_scripted_agent_reaches_the_gold_answer_within_budget(scenario: str) -> None:
    calls, submission = run(scenario, call)
    assert len(calls) <= MAX_TOOL_CALLS
    assert calls[0][0] == "get_trip_request"
    built = build_output(submission, GatesBookingOutput)  # the submit tool's own shape check
    result = verdict(scenario, plain_output(built))
    assert result["valid"] is True, result["message"]
    assert submission == case(scenario)["expected"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_broken_variants_of_the_scripted_answer_fail_with_their_reason(scenario: str) -> None:
    _, submission = run(scenario, call)
    for broken in case(scenario)["broken"]:
        result = verdict(scenario, {**submission, **broken["change"]})
        assert result["valid"] is False and result["message"].split(":")[0] == broken["reason"], (broken["why"], result["message"])
