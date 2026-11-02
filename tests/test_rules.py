"""The oracle's rules at every threshold, exactly at the limit and one unit past it, plus each ranking key,
the hotel rules and the brief's section 11 cross-policy row for Gates, on small synthetic worlds."""

import pytest

from plugin.rules import (
    allowed_cabin,
    banned_reason,
    compliant_hotels,
    is_domestic,
    is_late,
    local_minutes,
    lodging_cap,
    ranking,
)
from plugin.tools_dev.worldgen import itinerary, segment

AIRPORTS = {
    "SEA": {"code": "SEA", "city": "Seattle", "us_50_states_dc": True, "timezone": "America/Los_Angeles"},
    "BOS": {"code": "BOS", "city": "Boston", "us_50_states_dc": True, "timezone": "America/New_York"},
    "HNL": {"code": "HNL", "city": "Honolulu", "us_50_states_dc": True, "timezone": "Pacific/Honolulu"},
    "LHR": {"code": "LHR", "city": "London", "us_50_states_dc": False, "timezone": "Europe/London"},
    "MEX": {"code": "MEX", "city": "Mexico City", "us_50_states_dc": False, "timezone": "America/Mexico_City"},
}
CARRIERS = {code: {"code": code} for code in ("CW", "SJ")}  # CW is preferred, SJ is not


def world_of(*specs, hotels=()):
    """A world with itineraries (id, [(flight, origin, destination, depart_local, minutes)], economy fare)."""
    segments, itineraries = {}, {}
    for itinerary_id, flights, economy in specs:
        records = []
        for flight, origin, destination, depart, minutes in flights:
            carrier = flight.split()[0]
            record = segment(AIRPORTS, f"S{len(segments) + 1}", flight, carrier, carrier, origin, destination, depart, minutes)
            segments[record["segment_id"]] = record
            records.append(record)
        fares = {"economy": economy, "premium_economy": economy * 2, "business": economy * 4, "first": None}
        itineraries[itinerary_id] = itinerary(itinerary_id, records, fares)
    hotel_table = {
        hotel_id: {"hotel_id": hotel_id, "name": name, "brand": brand, "city": city, "rate_before_tax_cents": rate, "tax_cents": tax}
        for hotel_id, name, brand, city, rate, tax in hotels
    }
    return {"airports": AIRPORTS, "carriers": CARRIERS, "segments": segments, "itineraries": itineraries, "travelers": {}, "hotels": hotel_table}


def trip(origin="SEA", destination="BOS", date="2026-12-07", preferred="2026-12-07T09:00"):
    return {"scenario": "synthetic", "origin": origin, "destination": destination, "departure_date": date, "preferred_departure_local": preferred}


def cabin_of(flights, destination="BOS"):
    world = world_of(("X1", flights, 30000))
    return allowed_cabin(world, trip(destination=destination), world["itineraries"]["X1"])


@pytest.mark.parametrize(
    ("clock", "late"),
    [("20:59", False), ("21:00", False), ("21:01", True), ("23:59", True), ("00:00", True), ("00:30", True), ("04:59", True), ("05:00", False), ("12:00", False)],
)
def test_after_nine_pm_window(clock: str, late: bool) -> None:
    assert is_late(f"2026-12-07T{clock}") is late


@pytest.mark.parametrize(
    ("depart", "minutes", "cabin"),
    [
        ("21:01", 301, "business"),
        ("21:01", 300, "premium_economy"),  # exactly five hours does not exceed five
        ("21:00", 301, "premium_economy"),  # exactly 9:00pm is not after 9:00pm
        ("20:00", 360, "premium_economy"),  # the brief's 6h domestic 20:00 flight: not business
        ("00:30", 345, "business"),  # an overnight departure counts as after 9:00pm
        ("04:59", 301, "business"),
        ("05:00", 301, "premium_economy"),
    ],
)
def test_domestic_business_needs_a_late_long_segment(depart: str, minutes: int, cabin: str) -> None:
    assert cabin_of([("CW 1", "SEA", "BOS", f"2026-12-07T{depart}", minutes)]) == cabin


def test_late_and_long_must_be_the_same_segment() -> None:
    # A late one-hour hop then a long morning leg: neither flight qualifies by itself.
    hop_then_morning = [("CW 1", "SEA", "HNL", "2026-12-07T21:30", 55), ("CW 2", "HNL", "BOS", "2026-12-08T06:05", 345)]
    assert cabin_of(hop_then_morning) == "premium_economy"
    # An early short hop then a late long leg: the second flight qualifies by itself.
    hop_then_late = [("CW 1", "SEA", "HNL", "2026-12-07T08:00", 50), ("CW 2", "HNL", "BOS", "2026-12-07T23:30", 330)]
    assert cabin_of(hop_then_late) == "business"


@pytest.mark.parametrize(("minutes", "cabin"), [(300, "economy"), (301, "business")])
def test_international_threshold(minutes: int, cabin: str) -> None:
    assert cabin_of([("CW 1", "SEA", "MEX", "2026-12-07T08:00", minutes)], destination="MEX") == cabin


def test_international_legs_never_combine_and_departure_time_does_not_matter() -> None:
    assert cabin_of([("CW 1", "SEA", "BOS", "2026-12-07T08:00", 290), ("CW 2", "BOS", "LHR", "2026-12-07T17:00", 290)], destination="LHR") == "economy"


def test_cross_policy_sanity_row_gates() -> None:
    # Brief section 11: leg 1 = 360 in air, layover 90, leg 2 = 420 in air (elapsed 870): Gates gives business.
    world = world_of(("X1", [("CW 1", "SEA", "BOS", "2026-12-07T06:00", 360), ("CW 2", "BOS", "LHR", "2026-12-07T16:30", 420)], 100000))
    record = world["itineraries"]["X1"]
    assert (record["layover_minutes"], record["total_elapsed_minutes"], record["longest_segment_minutes"]) == ([90], 870, 420)
    assert allowed_cabin(world, trip(destination="LHR"), record) == "business"


def test_honolulu_is_domestic_and_london_is_not() -> None:
    world = world_of()
    assert is_domestic(world, trip(destination="HNL")) is True
    assert is_domestic(world, trip(destination="LHR")) is False


def ranked(*specs, preferred="2026-12-07T09:00"):
    return ranking(world_of(*specs), trip(preferred=preferred))


def test_key_1_nonstop_beats_preferred_and_fare() -> None:
    connecting = ("X1", [("CW 1", "SEA", "HNL", "2026-12-07T09:00", 200), ("CW 2", "HNL", "BOS", "2026-12-07T15:00", 200)], 10000)
    nonstop = ("X2", [("SJ 3", "SEA", "BOS", "2026-12-07T14:00", 300)], 90000)
    assert ranked(connecting, nonstop) == ["X2", "X1"]


def test_key_2_preferred_beats_fare() -> None:
    assert ranked(("X1", [("SJ 1", "SEA", "BOS", "2026-12-07T09:00", 300)], 10000), ("X2", [("CW 2", "SEA", "BOS", "2026-12-07T14:00", 300)], 90000)) == ["X2", "X1"]


def test_key_2_a_connection_is_preferred_only_when_every_segment_is() -> None:
    mixed = ("X1", [("CW 1", "SEA", "HNL", "2026-12-07T09:00", 200), ("SJ 2", "HNL", "BOS", "2026-12-07T15:00", 200)], 10000)
    pure = ("X2", [("CW 3", "SEA", "HNL", "2026-12-07T10:00", 200), ("CW 4", "HNL", "BOS", "2026-12-07T16:00", 200)], 90000)
    assert ranked(mixed, pure) == ["X2", "X1"]


def test_key_3_fare_beats_departure_time() -> None:
    assert ranked(("X1", [("CW 1", "SEA", "BOS", "2026-12-07T09:00", 300)], 30001), ("X2", [("CW 2", "SEA", "BOS", "2026-12-07T19:00", 300)], 30000)) == ["X2", "X1"]


def test_key_4_departure_distance_then_key_5_itinerary_id() -> None:
    early = ("X9", [("CW 1", "SEA", "BOS", "2026-12-07T08:00", 300)], 30000)
    late = ("X2", [("CW 2", "SEA", "BOS", "2026-12-07T10:00", 300)], 30000)
    near = ("X5", [("CW 3", "SEA", "BOS", "2026-12-07T09:30", 300)], 30000)
    assert ranked(early, late, near) == ["X5", "X2", "X9"]  # 30 min, then 60 vs 60 broken by id


def test_key_4_compares_full_date_and_time_across_midnight() -> None:
    after_midnight = ("X1", [("CW 1", "SEA", "BOS", "2026-12-07T00:30", 300)], 30000)
    late_evening = ("X2", [("CW 2", "SEA", "BOS", "2026-12-07T23:55", 300)], 30000)
    assert ranked(after_midnight, late_evening, preferred="2026-12-07T00:15") == ["X1", "X2"]  # 15 vs 1420 minutes


def test_no_candidate_is_an_error_not_a_guess() -> None:
    with pytest.raises(ValueError, match="no itinerary"):
        ranking(world_of(), trip())


def hotels_world(*rows, city="Boston"):
    return world_of(hotels=[(f"H{index}", name, brand, city, rate, tax) for index, (name, brand, rate, tax) in enumerate(rows, start=100)])


def chosen(*rows, city="Boston", destination="BOS"):
    return compliant_hotels(hotels_world(*rows, city=city), trip(destination=destination))[0]["name"]


def test_hotel_exactly_at_cap_is_allowed_and_one_cent_over_is_not() -> None:
    assert chosen(("At Cap", "Independent", 40000, 0), ("Over", "Independent", 40001, 0)) == "At Cap"
    with pytest.raises(ValueError, match="no compliant hotel"):
        chosen(("Over", "Independent", 40001, 0))


def test_a_banned_hotel_cheaper_than_the_allowed_one_is_skipped() -> None:
    assert chosen(("Four Seasons Hotel Boston", "Four Seasons", 30000, 0), ("Allowed", "Independent", 39000, 0)) == "Allowed"


def test_only_the_named_property_of_a_chain_is_banned() -> None:
    rows = [("Tampa Marriott Water Street", "Marriott", 20000, 0), ("Other Marriott", "Marriott", 21000, 0), ("Indie", "Independent", 22000, 0)]
    assert chosen(*rows) == "Other Marriott"
    assert banned_reason({"name": "Beverly Wilshire", "brand": "Independent"}) is not None
    assert banned_reason({"name": "The Charles Hotel", "brand": "Independent"}) is not None
    assert banned_reason({"name": "Charles River Inn", "brand": "Independent"}) is None


def test_taxes_never_count() -> None:
    assert chosen(("Low Rate High Tax", "Independent", 39000, 9000), ("High Rate Low Tax", "Independent", 39500, 100)) == "Low Rate High Tax"


def test_hotel_ties_break_by_hotel_id() -> None:
    world = world_of(hotels=[("H200", "Second", "Independent", "Boston", 35000, 0), ("H150", "First", "Independent", "Boston", 35000, 0)])
    assert compliant_hotels(world, trip())[0]["hotel_id"] == "H150"


@pytest.mark.parametrize(
    ("city", "cap"),
    [("Washington D.C.", 35000), ("Boston", 40000), ("New York City", 40000), ("San Francisco", 40000), ("Geneva", 40000), ("Paris", 45000), ("Tokyo", 45000), ("London", 47500), ("Seattle", 30000), ("Nairobi", 30000)],
)
def test_lodging_caps(city: str, cap: int) -> None:
    assert lodging_cap(city) == cap


@pytest.mark.parametrize("text", ["2026-12-07 09:00", "2026-12-07T24:00", "2026-12-07T09:60", "2026-13-01T09:00"])
def test_local_stamps_must_be_real(text: str) -> None:
    with pytest.raises(ValueError):
        local_minutes(text)
