"""The rank-gates-vendor-trip verdict, and the checks of its reference tool compute_travel_desk_booking.

The verifier computes the correct booking itself (rules.oracle over the bundled fixtures) and checks the
submitted one against it in stages, each a list of constraints with stable ids (the reason codes):

0. answer key: the pinned reference equals the verifier's own oracle (else the plugin is broken);
1. referential integrity: every ranked id is an itinerary of this trip, the hotel exists in its city;
2. internal consistency: the ranking repeats no id, leaves none out, and starts with the selected id;
3. policy decision against the oracle: selection, full order, cabin, hotel ban, hotel cap, cheapest hotel.

A stage is checked only when every earlier stage holds. The message names the first failing constraint
and how many more fail, with the rule and the numbers behind it. Shape problems (types, Enum values,
missing or extra fields) never get here: NanoAgent's build_output refuses them first. The score is 1.0
when every constraint holds, else 0.0.
"""

from .checks import UNEXPECTED, fixtures, plain, result
from .rules import (
    DURATION_OVER,
    KEY_NAMES,
    PREFERRED_CARRIERS,
    banned_reason,
    candidates,
    clock,
    clock_minutes,
    compliant_hotels,
    destination_city,
    is_domestic,
    is_late,
    lodging_cap,
    oracle,
    rank_key,
)
from .world import itinerary_segments

TEXT = {
    "reference-matches-oracle": "The pinned answer key equals the verifier's own oracle",
    "ranked-ids-exist": "Every ranked id names an itinerary in the inventory",
    "ranked-ids-serve-trip": "Every ranked itinerary leaves the origin on the departure date for the destination (G5)",
    "hotel-exists": "The hotel id names a hotel in the inventory",
    "hotel-in-destination": "The hotel is in the destination city (G9)",
    "ranked-unique": "No itinerary id is ranked twice",
    "ranked-complete": "Every candidate itinerary is ranked (G5)",
    "selected-is-first": "selected_itinerary_id is ranked_itinerary_ids[0] (G8)",
    "selected-correct": "The selected itinerary is the one G6 ranks first",
    "ranking-correct": "The whole order follows the G6 keys",
    "cabin-correct": "allowed_cabin is the highest cabin G1-G4 allow on the selected itinerary",
    "hotel-not-banned": "The hotel is not a non-reimbursable property (G11)",
    "hotel-within-cap": "The hotel's rate before taxes is at most the city's cap (G10)",
    "hotel-correct": "The hotel is the cheapest compliant one, ties by hotel_id (G9)",
}


def verify_input(value):
    return result(True, "input is valid")  # a scenario Enum member is all the input there is


def verify_output(input_value, output_value, workspace):
    try:
        world, scenario = fixtures(plain(input_value)["scenario"])
        key = oracle(world, scenario)
    except UNEXPECTED as error:
        return result(False, f"verifier-error: {error!r}")
    if plain(output_value) != key:
        return result(False, "compute_travel_desk_booking differs from the verifier's oracle", expected=key)
    return result(True, "the answer key matches the verifier's oracle")


def verify_task(arguments, output, reference, workspace):
    try:
        world, scenario = fixtures(plain(arguments)["scenario"])
        key = oracle(world, scenario)
        pinned = None if reference is None else plain(reference)
        return judge(world, scenario, key, pinned, plain(output))
    except UNEXPECTED as error:
        return result(False, f"verifier-error: {error!r}")


def judge(world, scenario, key, pinned, given):
    stages = [
        [("reference-matches-oracle", lambda: reference_problem(key, pinned))],
        [
            ("ranked-ids-exist", lambda: exist_problem(world, given)),
            ("ranked-ids-serve-trip", lambda: serve_problem(world, scenario, given)),
            ("hotel-exists", lambda: hotel_exists_problem(world, given)),
            ("hotel-in-destination", lambda: hotel_city_problem(world, scenario, given)),
        ],
        [
            ("ranked-unique", lambda: unique_problem(given)),
            ("ranked-complete", lambda: complete_problem(world, scenario, key, given)),
            ("selected-is-first", lambda: first_problem(given)),
        ],
        [
            ("selected-correct", lambda: selected_problem(world, scenario, key, given)),
            ("ranking-correct", lambda: ranking_problem(world, scenario, key, given)),
            ("cabin-correct", lambda: cabin_problem(world, scenario, key, given)),
            ("hotel-not-banned", lambda: banned_problem(world, given)),
            ("hotel-within-cap", lambda: cap_problem(world, scenario, given)),
            ("hotel-correct", lambda: hotel_problem(world, scenario, key, given)),
        ],
    ]
    constraints, blocked = [], None
    for stage in stages:
        for identifier, check in stage:
            if blocked is not None:
                constraints.append(entry(identifier, None, None, None, f"not checked: {blocked} failed"))
                continue
            problem = check()
            if problem is None:
                constraints.append(entry(identifier, True, None, None, ""))
            else:
                constraints.append(entry(identifier, False, *problem))
        failed = [item for item in constraints if item["ok"] is False]
        if failed and blocked is None:
            blocked = failed[0]["id"]
    failed = [item for item in constraints if item["ok"] is False]
    if not failed:
        summary = (
            f"the booking follows the travel-desk rules: {given['selected_itinerary_id']} first of "
            f"{len(given['ranked_itinerary_ids'])}, {given['allowed_cabin']} allowed, hotel {given['hotel_id']}"
        )
        return result(True, summary, constraints=constraints, expected=key)
    more = f" (+{len(failed) - 1} more)" if len(failed) > 1 else ""
    return result(False, f"{failed[0]['id']}: {failed[0]['message']}{more}", constraints=constraints, expected=key)


def entry(identifier, ok, expected, actual, message):
    return {"id": identifier, "constraint": TEXT[identifier], "ok": ok, "expected": expected, "actual": actual, "message": message}


# ---- explanations: the rule and the numbers behind a verdict -------------------------------------------


def segment_text(world, scenario, segment):
    minutes = segment["in_air_minutes"]
    length = f"{minutes} min {'>' if minutes > DURATION_OVER else 'not >'} {DURATION_OVER}"
    if not is_domestic(world, scenario):
        return f"{segment['flight']} {length}"
    departs = clock(clock_minutes(segment["depart_local"]))
    window = "in the late window" if is_late(segment["depart_local"]) else "not after 21:00 nor before 05:00"
    return f"{segment['flight']} departs {departs} ({window}), {length}"


def cabin_facts(world, scenario, itinerary_id):
    """Why an itinerary allows the cabin it does, in words."""
    itinerary = world["itineraries"][itinerary_id]
    segments = "; ".join(segment_text(world, scenario, segment) for segment in itinerary_segments(world, itinerary))
    if is_domestic(world, scenario):
        rule = "domestic: business needs one flight that both departs after 21:00 (or before 05:00) and flies > 300 min, else premium_economy"
    else:
        rule = "international: business needs one flight > 300 min, else economy"
    return f"{itinerary_id} is {rule}; {segments}"


def key_facts(world, scenario, itinerary_id):
    itinerary = world["itineraries"][itinerary_id]
    segments = itinerary_segments(world, itinerary)
    return {
        "connections": len(segments) - 1,
        "carriers": sorted({segment["marketing_carrier"] for segment in segments}),
        "departs": clock(clock_minutes(segments[0]["depart_local"])),
    }


def why_first(world, scenario, better, worse):
    """Which G6 key puts itinerary ``better`` ahead of ``worse``, with its numbers."""
    first = rank_key(world, scenario, world["itineraries"][better])
    second = rank_key(world, scenario, world["itineraries"][worse])
    index = next(position for position, (one, two) in enumerate(zip(first, second)) if one != two)
    good, bad = key_facts(world, scenario, better), key_facts(world, scenario, worse)
    preferred = clock(clock_minutes(scenario["preferred_departure_local"]))
    if index == 0:
        detail = f"{better} is nonstop, {worse} has {bad['connections']} connection(s)"
    elif index == 1:
        others = [code for code in bad["carriers"] if code not in PREFERRED_CARRIERS]
        detail = f"{better} flies only preferred carriers ({', '.join(good['carriers'])}), {worse} uses {', '.join(others)}"
    elif index == 2:
        detail = f"economy fare {first[2]} < {second[2]} cents"
    elif index == 3:
        detail = (
            f"{better} departs {good['departs']}, {first[3]} min from the preferred {preferred}; "
            f"{worse} departs {bad['departs']}, {second[3]} min"
        )
    else:
        detail = f"tied on every other key, and itinerary_id {better} < {worse}"
    return f"key {index + 1} ({KEY_NAMES[index]}): {detail}"


# ---- the checks: each returns None or (expected, actual, message) --------------------------------------


def reference_problem(key, pinned):
    if pinned is not None and pinned != key:
        return key, pinned, "the pinned answer key differs from the verifier's oracle, so the plugin itself is broken"
    return None


def exist_problem(world, given):
    unknown = sorted({item for item in given["ranked_itinerary_ids"] if item not in world["itineraries"]})
    if given["selected_itinerary_id"] not in world["itineraries"]:
        unknown = sorted({*unknown, given["selected_itinerary_id"]})
    if unknown:
        return None, unknown, f"not in the inventory: {', '.join(unknown)}"
    return None


def candidate_ids(world, scenario):
    return sorted(item["itinerary_id"] for item in candidates(world, scenario))


def serve_problem(world, scenario, given):
    allowed = candidate_ids(world, scenario)
    stray = sorted({item for item in given["ranked_itinerary_ids"] if item not in allowed})
    if stray:
        route = f"{scenario['origin']} to {scenario['destination']} on {scenario['departure_date']}"
        return allowed, stray, f"{', '.join(stray)} do(es) not fly {route}; the candidates are {', '.join(allowed)}"
    return None


def hotel_exists_problem(world, given):
    if given["hotel_id"] not in world["hotels"]:
        return None, given["hotel_id"], f"hotel {given['hotel_id']!r} is not in the inventory"
    return None


def hotel_city_problem(world, scenario, given):
    if given["hotel_id"] not in world["hotels"]:
        return None  # hotel-exists already fails
    city = destination_city(world, scenario)
    hotel = world["hotels"][given["hotel_id"]]
    if hotel["city"] != city:
        return city, hotel["city"], f"hotel {given['hotel_id']} ({hotel['name']}) is in {hotel['city']}, not the destination {city}"
    return None


def unique_problem(given):
    ranked = given["ranked_itinerary_ids"]
    repeated = sorted({item for item in ranked if ranked.count(item) > 1})
    if repeated:
        return None, repeated, f"ranked more than once: {', '.join(repeated)}"
    return None


def complete_problem(world, scenario, key, given):
    missing = sorted(set(key["ranked_itinerary_ids"]) - set(given["ranked_itinerary_ids"]))
    if missing:
        total = len(key["ranked_itinerary_ids"])
        return key["ranked_itinerary_ids"], given["ranked_itinerary_ids"], (
            f"the ranking leaves out {', '.join(missing)}; all {total} itineraries of the trip must be ranked"
        )
    return None


def first_problem(given):
    ranked, selected = given["ranked_itinerary_ids"], given["selected_itinerary_id"]
    if not ranked or ranked[0] != selected:
        head = ranked[0] if ranked else None
        return head, selected, f"selected {selected} but the ranking starts with {head}"
    return None


def selected_problem(world, scenario, key, given):
    best, chosen = key["selected_itinerary_id"], given["selected_itinerary_id"]
    if chosen == best:
        return None
    return best, chosen, f"{best} ranks above {chosen} by {why_first(world, scenario, best, chosen)}"


def ranking_problem(world, scenario, key, given):
    wanted, ranked = key["ranked_itinerary_ids"], given["ranked_itinerary_ids"]
    if ranked == wanted:
        return None
    position = next(index for index, (one, two) in enumerate(zip(wanted, ranked)) if one != two)
    better, worse = wanted[position], ranked[position]
    return wanted, ranked, (
        f"position {position + 1} holds {worse}, but {better} ranks above it by {why_first(world, scenario, better, worse)}"
    )


def cabin_problem(world, scenario, key, given):
    if given["allowed_cabin"] == key["allowed_cabin"]:
        return None
    facts = cabin_facts(world, scenario, key["selected_itinerary_id"])
    return key["allowed_cabin"], given["allowed_cabin"], f"{given['allowed_cabin']} instead of {key['allowed_cabin']}: {facts}"


def banned_problem(world, given):
    reason = banned_reason(world["hotels"][given["hotel_id"]])
    if reason is not None:
        return None, given["hotel_id"], f"hotel {given['hotel_id']}: {reason}, never reimbursable"
    return None


def cap_problem(world, scenario, given):
    hotel = world["hotels"][given["hotel_id"]]
    cap = lodging_cap(hotel["city"])
    if hotel["rate_before_tax_cents"] > cap:
        over = hotel["rate_before_tax_cents"] - cap
        return cap, hotel["rate_before_tax_cents"], (
            f"hotel {given['hotel_id']} ({hotel['name']}) costs {hotel['rate_before_tax_cents']} cents before tax, "
            f"{over} over {hotel['city']}'s cap of {cap}"
        )
    return None


def hotel_problem(world, scenario, key, given):
    if given["hotel_id"] == key["hotel_id"]:
        return None
    best = compliant_hotels(world, scenario)[0]
    city = destination_city(world, scenario)
    chosen = world["hotels"][given["hotel_id"]]
    return key["hotel_id"], given["hotel_id"], (
        f"the cheapest compliant hotel in {city} (cap {lodging_cap(city)} cents before tax) is {best['hotel_id']} "
        f"({best['name']}) at {best['rate_before_tax_cents']} cents, not {given['hotel_id']} at "
        f"{chosen['rate_before_tax_cents']}; taxes never count"
    )

