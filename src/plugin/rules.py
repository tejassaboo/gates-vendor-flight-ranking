"""The Gates Foundation Vendor Travel & Expense Policy (effective 7/1/2024) as this plugin's toy handbook
states it (src/plugin/data/handbook.md): the oracle that the reference tool and the verifier both run on
the bundled fixtures, plus the tool views built from the same records.

Byte-identical in src/plugin/ and verifier/ (a test checks the two copies), so it keeps to the
verifier's pure-stdlib rules. Every function is a pure function of the fixtures and one scenario.
"""

import json
import re
from pathlib import Path

from .world import day_number, itinerary_segments, load_world, search

# The foundation's preferred carriers in this toy world (fictional airlines; handbook G6).
PREFERRED_CARRIERS = ("CW", "NS", "RG", "TB")
DURATION_OVER = 300  # one flight (segment) must exceed this many in-air minutes for business (G2)
LATE_AFTER = 21 * 60  # "after 9:00pm": a segment leaves strictly after 21:00 local at its origin ... (G3)
LATE_BEFORE = 5 * 60  # ... or before 05:00 local (an overnight departure); 05:00 itself does not count
DEFAULT_LODGING_CAP = 30000  # USD cents per night before taxes, every city not listed below (G10)
LODGING_CAPS = {
    "Washington D.C.": 35000,
    "Boston": 40000,
    "New York City": 40000,
    "San Francisco": 40000,
    "Geneva": 40000,
    "Paris": 45000,
    "Tokyo": 45000,
    "London": 47500,
}
BANNED_BRANDS = ("Four Seasons",)  # any Four Seasons hotel or resort (G11)
BANNED_PROPERTIES = ("Beverly Wilshire", "The Charles Hotel", "Dream Nashville Hotel", "Tampa Marriott Water Street")
HOTEL_KEYS = ("hotel_id", "name", "brand", "city", "rate_before_tax_cents", "tax_cents")
LOCAL_STAMP = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})")
# The ranking keys in priority order, as the verifier names them (G6).
KEY_NAMES = ("nonstop", "preferred carrier", "economy fare", "departure-time distance", "itinerary_id")


def load_gates_world(data_dir):
    """The shared toy world plus this plugin's hotels table, each a dict from record id to record."""
    world = load_world(data_dir)
    records = json.loads((Path(data_dir) / "hotels.json").read_text(encoding="utf-8"))
    world["hotels"] = {record["hotel_id"]: record for record in records}
    return world


def hotel_problems(world):
    """Every way the hotels table breaks HOTEL_KEYS or names a city with no airport."""
    cities = {airport["city"] for airport in world["airports"].values()}
    problems = []
    for hotel_id, hotel in world["hotels"].items():
        if tuple(hotel) != HOTEL_KEYS:
            problems.append(f"hotel {hotel_id}: keys {list(hotel)} are not {list(HOTEL_KEYS)}")
        elif hotel["city"] not in cities:
            problems.append(f"hotel {hotel_id}: city {hotel['city']!r} has no airport")
    return problems


def local_minutes(text):
    """Minutes since 1970-01-01T00:00 of a local stamp YYYY-MM-DDTHH:MM (same clock only: no timezone)."""
    match = LOCAL_STAMP.fullmatch(text)
    if match is None:
        raise ValueError(f"{text!r} is not a local stamp YYYY-MM-DDTHH:MM")
    date, hour, minute = match.groups()
    if int(hour) > 23 or int(minute) > 59:
        raise ValueError(f"{text!r} is not a time of day")
    return day_number(date) * 1440 + int(hour) * 60 + int(minute)


def clock_minutes(text):
    """The time of day of a local stamp, in minutes after midnight."""
    return local_minutes(text) % 1440


def clock(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def airport_view(world, code):
    airport = world["airports"][code]
    return {key: airport[key] for key in ("code", "city", "country", "us_50_states_dc")}


def trip_request(world, scenario):
    """The trip request get_trip_request shows: the scenario's facts with its vendor and airports."""
    traveler = world["travelers"][scenario["traveler_id"]]
    return {
        "scenario": scenario["scenario"],
        "request_text": scenario["request_text"],
        "booking_date": scenario["booking_date"],
        "traveler": {
            "traveler_id": traveler["traveler_id"],
            "name": traveler["name"],
            "firm": traveler["department"],  # the shared schema's "department" holds the vendor's firm
            "base_point": traveler["base_point"],
        },
        "origin": airport_view(world, scenario["origin"]),
        "destination": airport_view(world, scenario["destination"]),
        "departure_date": scenario["departure_date"],
        "preferred_departure_local": scenario["preferred_departure_local"],
    }


def search_view(world, origin, destination, date):
    """What search_itineraries shows: every itinerary on the route and date, and its carriers with the
    foundation's preferred flag. It applies no other policy."""
    found = search(world, [origin], destination, date)
    codes = sorted(
        {
            segment[key]
            for itinerary in found
            for segment in itinerary_segments(world, itinerary)
            for key in ("marketing_carrier", "operating_carrier")
        }
    )
    return {
        "itineraries": [itinerary_view(world, itinerary) for itinerary in found],
        "carriers": [
            {"code": code, "name": world["carriers"][code]["name"], "preferred": code in PREFERRED_CARRIERS}
            for code in codes
        ],
    }


def itinerary_view(world, itinerary):
    segments = itinerary_segments(world, itinerary)
    keys = ("flight", "marketing_carrier", "operating_carrier", "origin", "destination", "depart_local", "arrive_local", "in_air_minutes")
    return {
        "itinerary_id": itinerary["itinerary_id"],
        "segments": [{key: segment[key] for key in keys} for segment in segments],
        "arrive_utc": segments[-1]["arrive_utc"],
        "fares_cents": dict(itinerary["fares_cents"]),
    }


def hotels_view(world, city):
    """What get_hotels shows: every hotel in the city, by hotel_id."""
    return {"city": city, "hotels": [dict(world["hotels"][key]) for key in sorted(world["hotels"]) if world["hotels"][key]["city"] == city]}


def is_domestic(world, scenario):
    """Domestic means both the origin and the destination are in the 50 US states or Washington D.C. (G1)."""
    airports = world["airports"]
    return airports[scenario["origin"]]["us_50_states_dc"] and airports[scenario["destination"]]["us_50_states_dc"]


def candidates(world, scenario):
    """Every itinerary from the trip's origin to its destination on its departure date (G5), by id."""
    found = search(world, [scenario["origin"]], scenario["destination"], scenario["departure_date"])
    if not found:
        raise ValueError(f"scenario {scenario['scenario']}: no itinerary serves the trip")
    return found


def first_departure(world, itinerary):
    return itinerary_segments(world, itinerary)[0]["depart_local"]


def is_nonstop(world, itinerary):
    return len(itinerary["segment_ids"]) == 1


def is_preferred(world, itinerary):
    """Every segment is sold under a preferred carrier's flight number."""
    return all(segment["marketing_carrier"] in PREFERRED_CARRIERS for segment in itinerary_segments(world, itinerary))


def departure_gap(world, scenario, itinerary):
    """Minutes between the first segment's local departure and the preferred departure (same airport clock)."""
    return abs(local_minutes(first_departure(world, itinerary)) - local_minutes(scenario["preferred_departure_local"]))


def rank_key(world, scenario, itinerary):
    """The lexicographic ranking key (G6): nonstop, preferred carrier, economy fare, departure-time distance, id."""
    return (
        0 if is_nonstop(world, itinerary) else 1,
        0 if is_preferred(world, itinerary) else 1,
        itinerary["fares_cents"]["economy"],
        departure_gap(world, scenario, itinerary),
        itinerary["itinerary_id"],
    )


def ranking(world, scenario):
    """Every candidate itinerary id, best first."""
    return [item["itinerary_id"] for item in sorted(candidates(world, scenario), key=lambda item: rank_key(world, scenario, item))]


def is_late(depart_local):
    """The departure counts as "after 9:00pm" (G3): later than 21:00 or earlier than 05:00, local clock."""
    minutes = clock_minutes(depart_local)
    return minutes > LATE_AFTER or minutes < LATE_BEFORE


def business_segments(world, scenario, itinerary):
    """The segments that by themselves allow business (G4): longer than DURATION_OVER in-air minutes and,
    on a domestic trip, also departing late at their own origin. Both conditions bind the same flight."""
    domestic = is_domestic(world, scenario)
    return [
        segment
        for segment in itinerary_segments(world, itinerary)
        if segment["in_air_minutes"] > DURATION_OVER and (not domestic or is_late(segment["depart_local"]))
    ]


def allowed_cabin(world, scenario, itinerary):
    """The highest cabin the policy allows on the itinerary (G4). First class is never allowed."""
    if business_segments(world, scenario, itinerary):
        return "business"
    return "premium_economy" if is_domestic(world, scenario) else "economy"


def lodging_cap(city):
    """The nightly cap before taxes in USD cents (G10)."""
    return LODGING_CAPS.get(city, DEFAULT_LODGING_CAP)


def banned_reason(hotel):
    """Why the property is never reimbursable (G11), or None when it may be used."""
    if hotel["brand"] in BANNED_BRANDS:
        return f"{hotel['name']} is a {hotel['brand']} property"
    if hotel["name"] in BANNED_PROPERTIES:
        return f"{hotel['name']} is named on the non-reimbursable list"
    return None


def destination_city(world, scenario):
    return world["airports"][scenario["destination"]]["city"]


def compliant_hotels(world, scenario):
    """The destination city's hotels that are not banned and cost at most its cap before taxes, cheapest
    first, ties by hotel_id (G9)."""
    city = destination_city(world, scenario)
    cap = lodging_cap(city)
    pool = [
        hotel
        for hotel in world["hotels"].values()
        if hotel["city"] == city and banned_reason(hotel) is None and hotel["rate_before_tax_cents"] <= cap
    ]
    if not pool:
        raise ValueError(f"scenario {scenario['scenario']}: no compliant hotel in {city}")
    return sorted(pool, key=lambda hotel: (hotel["rate_before_tax_cents"], hotel["hotel_id"]))


def oracle(world, scenario):
    """The one correct travel-desk booking for ``scenario``, as the task output's plain JSON."""
    ranked = ranking(world, scenario)
    return {
        "ranked_itinerary_ids": ranked,
        "selected_itinerary_id": ranked[0],
        "allowed_cabin": allowed_cabin(world, scenario, world["itineraries"][ranked[0]]),
        "hotel_id": compliant_hotels(world, scenario)[0]["hotel_id"],
    }
