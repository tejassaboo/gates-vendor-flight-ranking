"""The tools: what they return, what they refuse, how big their outputs are, and the real MCP server."""

import json
import sys

import anyio
import pytest
from helpers import ROOT, SCENARIOS
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from slimconfig import build_output, plain_output

import verifier
from contract import HotelsInput, ScenarioInput, SearchInput
from plugin import get_hotels, get_trip_request, search_itineraries

MAX_OUTPUT_CHARS = 6000  # about 1.5k tokens: every tool output stays far from the hosted 65,536-token budget


def trip(scenario):
    return get_trip_request(build_output({"scenario": scenario}, ScenarioInput))


def search(origin, destination, date):
    return search_itineraries(build_output({"origin": origin, "destination": destination, "date": date}, SearchInput))


def hotels(city):
    return get_hotels(build_output({"city": city}, HotelsInput))


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_tool_outputs_match_the_fixtures_and_stay_small(scenario: str) -> None:
    given = build_output({"scenario": scenario}, ScenarioInput)
    request = trip(scenario)
    assert verifier.verify_output("get_trip_request", given, request, ".")["valid"] is True
    assert len(json.dumps(plain_output(request))) <= MAX_OUTPUT_CHARS
    query = build_output({"origin": request.origin.code, "destination": request.destination.code, "date": request.departure_date}, SearchInput)
    found = search_itineraries(query)
    assert found.itineraries, "the step plan's search finds the scenario's flights"
    assert verifier.verify_output("search_itineraries", query, found, ".")["valid"] is True
    assert len(json.dumps(plain_output(found))) <= MAX_OUTPUT_CHARS
    city = build_output({"city": request.destination.city}, HotelsInput)
    listed = get_hotels(city)
    assert listed.hotels and verifier.verify_output("get_hotels", city, listed, ".")["valid"] is True
    assert len(json.dumps(plain_output(listed))) <= MAX_OUTPUT_CHARS


def test_search_flags_preferred_carriers_and_applies_no_policy() -> None:
    found = search("SEA", "BOS", "2026-12-07")
    assert {carrier.code: carrier.preferred for carrier in found.carriers} == {"CW": True, "HL": False, "NS": True, "PB": False, "SJ": False}
    assert search("SEA", "BOS", "2026-12-06").itineraries == []


def test_hotels_lists_banned_and_over_cap_properties_too() -> None:
    names = [hotel.name for hotel in hotels("London").hotels]
    assert "Four Seasons Hotel London at Park Lane" in names and "Kensington Wren House" in names


@pytest.mark.parametrize(
    ("origin", "destination", "date", "match"),
    [
        ("XXX", "BOS", "2026-12-07", "not an airport"),
        ("SEA", "bos", "2026-12-07", "not an airport"),
        ("SEA", "SEA", "2026-12-07", "must differ"),
        ("SEA", "BOS", "2026-12-32", "calendar date"),
    ],
)
def test_search_refuses_bad_input(origin, destination, date, match) -> None:
    with pytest.raises(ValueError, match=match):
        search(origin, destination, date)


@pytest.mark.parametrize("city", ["Atlantis", "boston", "Washington DC"])
def test_hotels_refuse_an_unknown_city(city: str) -> None:
    with pytest.raises(ValueError, match="no hotels"):
        hotels(city)


def test_a_changed_tool_output_is_caught() -> None:
    given = build_output({"city": "Boston"}, HotelsInput)
    listed = plain_output(hotels("Boston"))
    listed["hotels"][0]["rate_before_tax_cents"] += 1
    result = verifier.verify_output("get_hotels", given, build_output(listed, type(hotels("Boston"))), ".")
    assert result["valid"] is False and "hotels" in result["message"]


def test_the_mcp_server_serves_every_tool() -> None:
    async def session():
        server = StdioServerParameters(command=sys.executable, args=["-m", "plugin"], cwd=str(ROOT))
        async with stdio_client(server) as (read, write), ClientSession(read, write) as client:
            await client.initialize()
            names = sorted(tool.name for tool in (await client.list_tools()).tools)
            answer = await client.call_tool("get_trip_request", {"scenario": "seattle-headquarters-visit"})
            refused = await client.call_tool("get_hotels", {"city": "Atlantis"})
            return names, answer, refused

    names, answer, refused = anyio.run(session)
    assert names == ["compute_travel_desk_booking", "get_hotels", "get_trip_request", "search_itineraries"]
    assert answer.isError is False and answer.structuredContent["origin"]["code"] == "HNL"
    assert refused.isError is True
