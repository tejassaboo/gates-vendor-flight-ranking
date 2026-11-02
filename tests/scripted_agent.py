"""A scripted agent with no LLM, written from the handbook (src/plugin/data/handbook.md) alone: it imports
nothing of the plugin's rules. It follows the step plan through a ``call(tool, arguments)`` function and
returns the submission it would make, so the tests can run each scenario end to end. Steps 2's two calls
are one reply in the plan; they are listed here as two calls."""

from datetime import datetime

CAPS = {"Washington D.C.": 35000, "Boston": 40000, "New York City": 40000, "San Francisco": 40000, "Geneva": 40000}
CAPS |= {"Paris": 45000, "Tokyo": 45000, "London": 47500}
BANNED_NAMES = {"Beverly Wilshire", "The Charles Hotel", "Dream Nashville Hotel", "Tampa Marriott Water Street"}


def local(stamp):
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M")


def late(stamp):
    """G3: later than 21:00 or earlier than 05:00 on the local clock."""
    moment = local(stamp)
    minutes = moment.hour * 60 + moment.minute
    return minutes > 21 * 60 or minutes < 5 * 60


def cabin(domestic, itinerary):
    """G4: business when one segment by itself qualifies."""
    for segment in itinerary["segments"]:
        if segment["in_air_minutes"] > 300 and (not domestic or late(segment["depart_local"])):
            return "business"
    return "premium_economy" if domestic else "economy"


def run(scenario, call):
    """(the tool calls made, in order, as (tool, arguments); the submission)."""
    calls = [("get_trip_request", {"scenario": scenario})]
    request = call(*calls[-1])
    origin, destination = request["origin"], request["destination"]
    calls.append(("search_itineraries", {"origin": origin["code"], "destination": destination["code"], "date": request["departure_date"]}))
    found = call(*calls[-1])
    calls.append(("get_hotels", {"city": destination["city"]}))
    hotels = call(*calls[-1])["hotels"]
    preferred = {carrier["code"] for carrier in found["carriers"] if carrier["preferred"]}
    wanted = local(request["preferred_departure_local"])

    def key(itinerary):
        segments = itinerary["segments"]
        gap = abs((local(segments[0]["depart_local"]) - wanted).total_seconds()) // 60
        all_preferred = all(segment["marketing_carrier"] in preferred for segment in segments)
        return (len(segments) != 1, not all_preferred, itinerary["fares_cents"]["economy"], gap, itinerary["itinerary_id"])

    ranked = sorted(found["itineraries"], key=key)
    domestic = origin["us_50_states_dc"] and destination["us_50_states_dc"]
    cap = CAPS.get(destination["city"], 30000)
    allowed = [
        hotel
        for hotel in hotels
        if hotel["brand"] != "Four Seasons" and hotel["name"] not in BANNED_NAMES and hotel["rate_before_tax_cents"] <= cap
    ]
    hotel = min(allowed, key=lambda item: (item["rate_before_tax_cents"], item["hotel_id"]))
    return calls, {
        "ranked_itinerary_ids": [item["itinerary_id"] for item in ranked],
        "selected_itinerary_id": ranked[0]["itinerary_id"],
        "allowed_cabin": cabin(domestic, ranked[0]),
        "hotel_id": hotel["hotel_id"],
    }
