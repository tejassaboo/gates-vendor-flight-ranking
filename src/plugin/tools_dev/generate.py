"""The seeded generator of this plugin's fixtures (development only): `uv run python -m plugin.tools_dev.generate`
rewrites src/plugin/data/ (except handbook.md). The committed files are the source of truth; a test checks
this generator still reproduces them byte for byte.

Each scenario's flights and hotels are written out by hand, because each one sets a trap from the brief
(TRAVEL_POLICY_TASKS_CONTEXT.md section 4, T2); the seed only scatters the itinerary and hotel ids, so the
right answer is never simply the first or lowest id. Airlines, flight numbers, fares and every hotel except
the policy's named non-reimbursable properties are fictional; all rates are synthetic. Expected answers are
not written here: they live in tests/cases/.
"""

import random
from pathlib import Path

from plugin.tools_dev.worldgen import itinerary, json_text, segment

SEED = 20240701
DATA = Path(__file__).resolve().parents[1] / "data"

AIRPORTS = [
    # code, city (as get_hotels names it), country, continental US, US 50 states + DC, IANA timezone
    ("BNA", "Nashville", "US", True, True, "America/Chicago"),
    ("BOS", "Boston", "US", True, True, "America/New_York"),
    ("DCA", "Washington D.C.", "US", True, True, "America/New_York"),
    ("DEN", "Denver", "US", True, True, "America/Denver"),
    ("AMS", "Amsterdam", "NL", False, False, "Europe/Amsterdam"),
    ("DXB", "Dubai", "AE", False, False, "Asia/Dubai"),
    ("HNL", "Honolulu", "US", False, True, "Pacific/Honolulu"),
    ("JFK", "New York City", "US", True, True, "America/New_York"),
    ("LAX", "Los Angeles", "US", True, True, "America/Los_Angeles"),
    ("LHR", "London", "GB", False, False, "Europe/London"),
    ("MEX", "Mexico City", "MX", False, False, "America/Mexico_City"),
    ("MIA", "Miami", "US", True, True, "America/New_York"),
    ("MSP", "Minneapolis", "US", True, True, "America/Chicago"),
    ("NBO", "Nairobi", "KE", False, False, "Africa/Nairobi"),
    ("ORD", "Chicago", "US", True, True, "America/Chicago"),
    ("PDX", "Portland", "US", True, True, "America/Los_Angeles"),
    ("SEA", "Seattle", "US", True, True, "America/Los_Angeles"),
    ("TPA", "Tampa", "US", True, True, "America/New_York"),
]

CARRIERS = [
    # code, name, US flag carrier, code-share partners (none: every flight here is flown by its seller)
    ("CW", "Cascade Airways", True, []),
    ("GP", "Gulfpearl", False, []),
    ("HL", "Heartland Air", True, []),
    ("NS", "Northstar Air", True, []),
    ("PB", "Pelican Bay Airlines", True, []),
    ("RG", "Regent Airways", False, []),
    ("SJ", "Sunjet", True, []),
    ("SM", "Sierra Madre Air", False, []),
    ("TB", "Tulip Blue", False, []),
]

TRAVELERS = [
    # id, name, vendor firm (stored in the shared schema's "department"), base point
    ("V201", "Dana Whitfield", "Northbeam Facilitation", "Seattle, WA"),
    ("V202", "Priya Raman", "Kestrel Evaluation Partners", "Seattle, WA"),
    ("V203", "Marisol Ortega", "Tidewater Health Analytics", "Seattle, WA"),
    ("V204", "Tomás Herrera", "Maizal Nutrition Labs", "Seattle, WA"),
    ("V205", "Grace Liu", "Ridgeline Lab Quality", "Seattle, WA"),
    ("V206", "Oliver Bramwell", "Lanternfish Communications", "Seattle, WA"),
    ("V207", "Hannah Feld", "Capitol Ledger Policy Group", "Seattle, WA"),
    ("V208", "Wanjiru Kamau", "Highland Field Research", "Seattle, WA"),
    ("V209", "Marcus Bell", "Brightpath Learning Studio", "Seattle, WA"),
    ("V210", "Rosa Delgado", "Mangrove Event Design", "Seattle, WA"),
    ("V211", "Keoni Kahale", "Pacific Atoll Data", "Honolulu, HI"),
    ("V212", "Ines Carvalho", "Stillwater Vector Labs", "Portland, OR"),
]


def fares(economy, premium_economy, business, first=None):
    return {"economy": economy, "premium_economy": premium_economy, "business": business, "first": first}


def facts(scenario, traveler_id, origin, destination, departure_date, preferred_departure_local, request_text):
    return {
        "scenario": scenario,
        "request_text": request_text,
        "booking_date": "2026-11-02",
        "traveler_id": traveler_id,
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "preferred_departure_local": preferred_departure_local,
    }


# Per scenario: its facts, its itineraries as (segments, fares), each segment
# (flight, marketing carrier, operating carrier, origin, destination, local departure, in-air minutes),
# and the hotels it adds to its destination city as (name, brand, rate before tax, tax), in cents.
SCENARIOS = [
    {
        "facts": facts(
            "boston-board-retreat", "V201", "SEA", "BOS", "2026-12-07", "2026-12-07T21:30",
            "I'm facilitating the grantee board retreat in Boston on the morning of December 8, so I need to fly "
            "overnight on the 7th, ideally leaving around 9:30pm. The Northstar flight leaves at 9:00pm sharp, which "
            "is after 9 for all practical purposes, so business should be fine; my colleague always flies business "
            "on this route. Please add the lounge pass, and the Four Seasons is right by the venue.",
        ),
        "itineraries": [
            ([("NS 902", "NS", "NS", "SEA", "BOS", "2026-12-07T21:00", 331)], fares(29900, 44800, 109500)),
            ([("CW 488", "CW", "CW", "SEA", "BOS", "2026-12-07T21:01", 327)], fares(31200, 45800, 112000)),
            ([("CW 470", "CW", "CW", "SEA", "BOS", "2026-12-07T20:55", 333)], fares(31200, 46100, 113400)),
            ([("SJ 61", "SJ", "SJ", "SEA", "BOS", "2026-12-07T22:10", 319)], fares(24800, 33900, 89900)),
            (
                [("NS 455", "NS", "NS", "SEA", "MSP", "2026-12-07T07:00", 200), ("NS 1820", "NS", "NS", "MSP", "BOS", "2026-12-07T13:30", 165)],
                fares(21900, 36400, 98800),
            ),
            (
                [("HL 2207", "HL", "HL", "SEA", "ORD", "2026-12-07T06:15", 240), ("HL 418", "HL", "HL", "ORD", "BOS", "2026-12-07T13:20", 135)],
                fares(19400, 30100, 84600),
            ),
        ],
        "hotels": [
            ("Four Seasons Hotel Boston", "Four Seasons", 37900, 6300),
            ("Beacon Hill Lantern Inn", "Independent", 38600, 6400),
            ("Harborview Commons Hotel", "Commons Collection", 39950, 6600),
            ("Back Bay Ledger Hotel", "Ledger Hotels", 41200, 6800),
        ],
    },
    {
        "facts": facts(
            "new-york-donor-briefing", "V202", "SEA", "JFK", "2026-12-08", "2026-12-08T22:00",
            "I'm presenting the evaluation findings at the donor briefing in Manhattan first thing on December 9, so "
            "I'll take a late flight on the 8th, ideally around 10pm. Economy is fine if business isn't allowed. I'll "
            "also be hosting a working dinner for two, about $190, so please make sure that's covered.",
        ),
        "itineraries": [
            ([("CW 210", "CW", "CW", "SEA", "JFK", "2026-12-08T21:01", 318)], fares(28400, 41900, 104800)),
            ([("NS 1404", "NS", "NS", "SEA", "JFK", "2026-12-08T22:30", 312)], fares(29600, 43300, 107200)),
            ([("SJ 18", "SJ", "SJ", "SEA", "JFK", "2026-12-08T23:05", 309)], fares(22900, 31800, 86400)),
            (
                [("NS 610", "NS", "NS", "SEA", "MSP", "2026-12-08T12:00", 195), ("NS 1932", "NS", "NS", "MSP", "JFK", "2026-12-08T18:10", 150)],
                fares(24500, 37800, 96100),
            ),
            (
                [("CW 330", "CW", "CW", "SEA", "DEN", "2026-12-08T06:00", 150), ("CW 1188", "CW", "CW", "DEN", "JFK", "2026-12-08T10:30", 230)],
                fares(23100, 35200, 93400),
            ),
        ],
        "hotels": [
            ("Bryant Park Meridian", "Meridian House", 36500, 5800),
            ("Hudson Yards Lodge", "Independent", 38800, 6200),
            ("Midtown Atrium Hotel", "Atrium Stays", 40500, 6500),
            ("Four Seasons Hotel New York Downtown", "Four Seasons", 52000, 8300),
        ],
    },
    {
        "facts": facts(
            "honolulu-health-workshop", "V203", "SEA", "HNL", "2027-01-14", "2027-01-14T20:00",
            "Heading to Honolulu for the Pacific islands disease-surveillance workshop. I'd like the 8pm departure on "
            "January 14. It's six hours over open ocean, which is basically an international flight, so business "
            "please. For the hotel, the Ko Olina Four Seasons has a great rate, or any place under $300 a night "
            "all-in.",
        ),
        "itineraries": [
            ([("CW 845", "CW", "CW", "SEA", "HNL", "2027-01-14T20:00", 360)], fares(38900, 55400, 129000)),
            ([("CW 851", "CW", "CW", "SEA", "HNL", "2027-01-14T08:15", 355)], fares(41800, 58900, 134500)),
            ([("NS 1500", "NS", "NS", "SEA", "HNL", "2027-01-14T21:30", 362)], fares(43500, 60200, 138000)),
            ([("SJ 707", "SJ", "SJ", "SEA", "HNL", "2027-01-14T13:00", 350)], fares(33900, 47800, 112500)),
            (
                [("CW 220", "CW", "CW", "SEA", "LAX", "2027-01-14T06:00", 165), ("CW 1610", "CW", "CW", "LAX", "HNL", "2027-01-14T10:00", 340)],
                fares(36200, 52800, 125600),
            ),
        ],
        "hotels": [
            ("Four Seasons Resort Oahu at Ko Olina", "Four Seasons", 25500, 4600),
            ("Kaimana Reef Hotel", "Independent", 27200, 5600),
            ("Manoa Garden Inn", "Garden Inns", 28400, 1400),
            ("Waikiki Shoreline Tower", "Shoreline Resorts", 31500, 5200),
        ],
    },
    {
        "facts": facts(
            "mexico-city-nutrition-summit", "V204", "SEA", "MEX", "2027-01-19", "2027-01-19T08:00",
            "I'm a panelist at the maize-fortification summit in Mexico City and fly down on January 19, ideally "
            "around 8am. Economy is fine honestly; I don't want to look extravagant on a foundation trip, so please "
            "just book the cheapest seat and note economy as my cabin.",
        ),
        "itineraries": [
            ([("CW 1260", "CW", "CW", "SEA", "MEX", "2027-01-19T08:10", 301)], fares(46500, 63900, 141000)),
            ([("CW 1264", "CW", "CW", "SEA", "MEX", "2027-01-19T13:40", 298)], fares(46500, 64400, 142500)),
            ([("SM 405", "SM", "SM", "SEA", "MEX", "2027-01-19T07:30", 300)], fares(39800, 55100, 121000)),
            (
                [("NS 726", "NS", "NS", "SEA", "LAX", "2027-01-19T06:00", 165), ("NS 2290", "NS", "NS", "LAX", "MEX", "2027-01-19T11:00", 210)],
                fares(41200, 57600, 128800),
            ),
            (
                [("SJ 140", "SJ", "SJ", "SEA", "LAX", "2027-01-19T07:15", 165), ("SM 913", "SM", "SM", "LAX", "MEX", "2027-01-19T12:00", 215)],
                fares(35500, 49900, 112000),
            ),
        ],
        "hotels": [
            ("Hotel Reforma Jacarandas", "Independent", 18900, 3400),
            ("Casa Roma Suites", "Casa Hotels", 21400, 3800),
            ("Four Seasons Hotel Mexico City", "Four Seasons", 29500, 5300),
            ("Polanco Vista Hotel", "Vista Group", 31200, 5600),
        ],
    },
    {
        "facts": facts(
            "mexico-city-lab-audit", "V205", "SEA", "MEX", "2027-02-02", "2027-02-02T07:30",
            "Back to Mexico City on February 2 for the reference-lab quality audit, ideally leaving around 7:30am. I "
            "start the audit the afternoon I land and it's a five-hour flight, so I'd really like business class. "
            "The 1:40pm Cascade flight is over five hours if that helps.",
        ),
        "itineraries": [
            ([("CW 1260", "CW", "CW", "SEA", "MEX", "2027-02-02T08:10", 300)], fares(44800, 61900, 138000)),
            ([("CW 1264", "CW", "CW", "SEA", "MEX", "2027-02-02T13:40", 301)], fares(47900, 65300, 144500)),
            ([("SM 405", "SM", "SM", "SEA", "MEX", "2027-02-02T07:30", 302)], fares(38600, 53800, 119000)),
            (
                [("NS 726", "NS", "NS", "SEA", "LAX", "2027-02-02T06:00", 165), ("NS 2290", "NS", "NS", "LAX", "MEX", "2027-02-02T11:00", 210)],
                fares(40100, 56300, 126500),
            ),
        ],
        "hotels": [],
    },
    {
        "facts": facts(
            "london-global-health-convening", "V206", "SEA", "LHR", "2027-02-09", "2027-02-09T13:00",
            "I'm running communications for the global health convening in London and fly out February 9, ideally "
            "around 1pm. Please book the Four Seasons Park Lane, it's next to the venue and still under the London "
            "limit, and add a lounge pass for the layover if there is one.",
        ),
        "itineraries": [
            ([("RG 48", "RG", "RG", "SEA", "LHR", "2027-02-09T13:30", 575)], fares(98400, 152000, 389000)),
            ([("SJ 2", "SJ", "SJ", "SEA", "LHR", "2027-02-09T19:05", 570)], fares(84200, 131000, 342000)),
            (
                [("TB 6", "TB", "TB", "SEA", "AMS", "2027-02-09T12:50", 590), ("TB 1009", "TB", "TB", "AMS", "LHR", "2027-02-10T09:30", 75)],
                fares(91000, 141500, 366000),
            ),
            (
                [("HL 2207", "HL", "HL", "SEA", "ORD", "2027-02-09T06:15", 240), ("HL 98", "HL", "HL", "ORD", "LHR", "2027-02-09T17:45", 470)],
                fares(79900, 124800, 331000),
            ),
        ],
        "hotels": [
            ("Four Seasons Hotel London at Park Lane", "Four Seasons", 44500, 8900),
            ("Bloomsbury Quill Hotel", "Independent", 47500, 9500),
            ("Southbank Lantern Hotel", "Lantern Hotels", 47501, 9500),
            ("Kensington Wren House", "Wren Collection", 49900, 9900),
        ],
    },
    {
        "facts": facts(
            "washington-policy-roundtable", "V207", "SEA", "DCA", "2027-01-26", "2027-01-26T09:00",
            "Booking DC for the immunization-financing roundtable on Capitol Hill. I fly January 26 and honestly the "
            "8am and the 10am are equally good for me; 9am would be ideal. My colleague always stays at the Four "
            "Seasons in Georgetown, but anything near Dupont works.",
        ),
        "itineraries": [
            ([("CW 6", "CW", "CW", "SEA", "DCA", "2027-01-26T08:00", 290)], fares(33100, 47200, 116000)),
            ([("NS 1122", "NS", "NS", "SEA", "DCA", "2027-01-26T10:00", 292)], fares(33100, 47900, 117500)),
            ([("CW 14", "CW", "CW", "SEA", "DCA", "2027-01-26T12:45", 289)], fares(35900, 49800, 121800)),
            ([("SJ 300", "SJ", "SJ", "SEA", "DCA", "2027-01-26T23:15", 281)], fares(26900, 37400, 95400)),
            (
                [("HL 2207", "HL", "HL", "SEA", "ORD", "2027-01-26T06:15", 240), ("HL 512", "HL", "HL", "ORD", "DCA", "2027-01-26T13:40", 125)],
                fares(24400, 35100, 90200),
            ),
        ],
        "hotels": [
            ("Dupont Ivy Hotel", "Independent", 34500, 5100),
            ("Capitol Lantern Suites", "Lantern Hotels", 34800, 5100),
            ("Foggy Bottom Commons", "Commons Collection", 35100, 5200),
            ("Four Seasons Hotel Washington DC", "Four Seasons", 61000, 9100),
        ],
    },
    {
        "facts": facts(
            "nairobi-field-mission", "V208", "SEA", "NBO", "2027-02-16", "2027-02-16T12:00",
            "Field mission to Nairobi for the county health-records pilot, leaving February 16 around noon. I'm "
            "Gulfpearl gold, so please book Gulfpearl through Dubai; it's cheaper anyway and I'll keep my status. "
            "I'll also host the county health team for dinner, about $220, so please include that.",
        ),
        "itineraries": [
            (
                [("TB 6", "TB", "TB", "SEA", "AMS", "2027-02-16T12:50", 590), ("TB 565", "TB", "TB", "AMS", "NBO", "2027-02-17T10:20", 500)],
                fares(142000, 218000, 512000),
            ),
            (
                [("GP 230", "GP", "GP", "SEA", "DXB", "2027-02-16T17:40", 870), ("GP 719", "GP", "GP", "DXB", "NBO", "2027-02-17T23:55", 300)],
                fares(118500, 184000, 455000),
            ),
            (
                [("RG 48", "RG", "RG", "SEA", "LHR", "2027-02-16T13:30", 575), ("RG 65", "RG", "RG", "LHR", "NBO", "2027-02-17T10:15", 505)],
                fares(139500, 214500, 506000),
            ),
            (
                [("SJ 9", "SJ", "SJ", "SEA", "JFK", "2027-02-16T07:00", 310), ("GP 744", "GP", "GP", "JFK", "NBO", "2027-02-16T19:40", 900)],
                fares(121000, 188500, 462000),
            ),
        ],
        "hotels": [
            ("Gigiri Acacia Hotel", "Independent", 21800, 3500),
            ("Westlands Baobab Suites", "Baobab Hotels", 24400, 3900),
            ("Karen Hills Lodge", "Independent", 30500, 4900),
        ],
    },
    {
        "facts": facts(
            "nashville-education-summit", "V209", "SEA", "BNA", "2027-01-21", "2027-01-21T07:00",
            "Demoing our adaptive-math curriculum at the education summit in Nashville on January 21, ideally on an "
            "early flight around 7am. Connecting through Minneapolis on Northstar is cheaper and they're one of the "
            "foundation's preferred airlines, so I'm happy with that. The Dream Nashville has the best rate downtown.",
        ),
        "itineraries": [
            ([("SJ 1450", "SJ", "SJ", "SEA", "BNA", "2027-01-21T07:20", 252)], fares(30900, 43800, 104000)),
            (
                [("NS 455", "NS", "NS", "SEA", "MSP", "2027-01-21T06:00", 195), ("NS 1288", "NS", "NS", "MSP", "BNA", "2027-01-21T12:20", 125)],
                fares(26800, 38900, 96500),
            ),
            (
                [("CW 330", "CW", "CW", "SEA", "DEN", "2027-01-21T06:30", 150), ("CW 1544", "CW", "CW", "DEN", "BNA", "2027-01-21T11:05", 145)],
                fares(27900, 40200, 98900),
            ),
            (
                [("HL 2207", "HL", "HL", "SEA", "ORD", "2027-01-21T06:15", 240), ("HL 611", "HL", "HL", "ORD", "BNA", "2027-01-21T13:30", 105)],
                fares(23900, 34600, 88800),
            ),
        ],
        "hotels": [
            ("Dream Nashville Hotel", "Dream Hotels", 21900, 3700),
            ("Music Row Porchlight Inn", "Independent", 23800, 4000),
            ("The Gulch Foundry Hotel", "Foundry Hotels", 26500, 4500),
            ("Broadway Neon Suites", "Independent", 31000, 5300),
        ],
    },
    {
        "facts": facts(
            "tampa-grantee-expo", "V210", "SEA", "TPA", "2027-02-23", "2027-02-23T09:00",
            "Setting up the foundation's booth at the grantee expo in Tampa; I fly February 23, ideally around 9am. "
            "I'm bringing two checked bags of display banners, so please cover both. I'm a Marriott loyalty member "
            "and the Water Street Marriott is closest to the convention center.",
        ),
        "itineraries": [
            ([("CW 1702", "CW", "CW", "SEA", "TPA", "2027-02-23T09:05", 318)], fares(35400, 50100, 122000)),
            ([("PB 88", "PB", "PB", "SEA", "TPA", "2027-02-23T23:30", 305)], fares(29900, 41800, 101500)),
            (
                [("NS 455", "NS", "NS", "SEA", "MSP", "2027-02-23T06:00", 195), ("NS 1670", "NS", "NS", "MSP", "TPA", "2027-02-23T12:30", 190)],
                fares(31200, 44600, 108800),
            ),
            (
                [("HL 2207", "HL", "HL", "SEA", "ORD", "2027-02-23T06:15", 240), ("HL 735", "HL", "HL", "ORD", "TPA", "2027-02-23T13:25", 165)],
                fares(27700, 39400, 96000),
            ),
        ],
        "hotels": [
            ("Tampa Marriott Water Street", "Marriott", 23900, 3600),
            ("Harbour Island Marriott Tampa", "Marriott", 25400, 3800),
            ("Ybor Cigar Factory Hotel", "Independent", 26900, 4000),
            ("Bayshore Palms Inn", "Palms Inns", 28800, 4300),
        ],
    },
    {
        "facts": facts(
            "seattle-headquarters-visit", "V211", "HNL", "SEA", "2027-01-28", "2027-01-28T00:15",
            "Coming to the foundation's Seattle headquarters for the data-sharing workshop. I'd take the overnight "
            "flight just after midnight, the early hours of January 28. A 12:30 a.m. departure is technically a "
            "morning flight, not an after-9pm one, so I assume premium economy is my limit. Any hotel near South "
            "Lake Union is fine.",
        ),
        "itineraries": [
            ([("CW 2", "CW", "CW", "HNL", "SEA", "2027-01-28T00:30", 345)], fares(34900, 50100, 119800)),
            ([("NS 8", "NS", "NS", "HNL", "SEA", "2027-01-28T09:15", 340)], fares(36600, 52300, 124000)),
            ([("CW 10", "CW", "CW", "HNL", "SEA", "2027-01-28T13:00", 338)], fares(38100, 53900, 127800)),
            ([("SJ 33", "SJ", "SJ", "HNL", "SEA", "2027-01-28T23:55", 336)], fares(29400, 41200, 99800)),
        ],
        "hotels": [
            ("Four Seasons Hotel Seattle", "Four Seasons", 27500, 4300),
            ("Pike Street Ferry Hotel", "Independent", 28900, 4500),
            ("South Lake Union Loft", "Loft Hotels", 29900, 4700),
            ("Belltown Cedar Hotel", "Independent", 33500, 5200),
        ],
    },
    {
        "facts": facts(
            "miami-vector-lab-demo", "V212", "PDX", "MIA", "2027-02-01", "2027-02-01T21:00",
            "Demonstrating our mosquito-surveillance traps at the vector-control lab in Miami. I'd leave Portland on "
            "the evening of February 1 around 9pm, overnight in Seattle with family, and take the early flight to "
            "Miami. My trip starts after 9pm and includes a flight of over five hours, so business should apply.",
        ),
        "itineraries": [
            (
                [("CW 2210", "CW", "CW", "PDX", "SEA", "2027-02-01T21:30", 55), ("CW 1906", "CW", "CW", "SEA", "MIA", "2027-02-02T06:05", 345)],
                fares(30400, 44200, 111000),
            ),
            (
                [("NS 2214", "NS", "NS", "PDX", "SEA", "2027-02-01T20:00", 50), ("NS 1930", "NS", "NS", "SEA", "MIA", "2027-02-01T23:30", 330)],
                fares(31800, 45900, 114600),
            ),
            (
                [("SJ 512", "SJ", "SJ", "PDX", "DEN", "2027-02-01T07:00", 150), ("SJ 1180", "SJ", "SJ", "DEN", "MIA", "2027-02-01T11:40", 235)],
                fares(26200, 37100, 92800),
            ),
            (
                [("HL 1207", "HL", "HL", "PDX", "ORD", "2027-02-01T06:30", 240), ("HL 774", "HL", "HL", "ORD", "MIA", "2027-02-01T13:30", 175)],
                fares(27500, 38800, 95900),
            ),
        ],
        "hotels": [
            ("Four Seasons Hotel Miami", "Four Seasons", 26800, 4600),
            ("Coral Way Courtyard Inn", "Independent", 27900, 4700),
            ("Brickell Tide Hotel", "Tide Hotels", 29300, 5000),
            ("Wynwood Mural House", "Independent", 32400, 5500),
        ],
    },
]


def build():
    """Every fixture file this generator writes: {path relative to data/: its text}."""
    airports = {
        code: {"code": code, "city": city, "country": country, "continental_us": continental, "us_50_states_dc": us, "timezone": tz}
        for code, city, country, continental, us, tz in sorted(AIRPORTS)
    }
    carriers = [
        {"code": code, "name": name, "us_flag_carrier": us_flag, "codeshare_partners": partners}
        for code, name, us_flag, partners in CARRIERS
    ]
    travelers = [
        {"traveler_id": traveler_id, "name": name, "department": firm, "base_point": base}
        for traveler_id, name, firm, base in TRAVELERS
    ]
    rng = random.Random(SEED)
    itinerary_numbers = rng.sample(range(100, 1000), sum(len(scenario["itineraries"]) for scenario in SCENARIOS))
    hotel_numbers = rng.sample(range(100, 1000), sum(len(scenario["hotels"]) for scenario in SCENARIOS))
    segments, itineraries, hotels, files = {}, [], [], {}
    for scenario in SCENARIOS:
        for flights, fare_table in scenario["itineraries"]:
            records = []
            for spec in flights:
                if spec not in segments:
                    segments[spec] = segment(airports, f"S{len(segments) + 1:03d}", *spec)
                records.append(segments[spec])
            itineraries.append(itinerary(f"I{itinerary_numbers[len(itineraries)]}", records, fare_table))
        city = airports[scenario["facts"]["destination"]]["city"]
        for name, brand, rate, tax in scenario["hotels"]:
            hotels.append(
                {
                    "hotel_id": f"H{hotel_numbers[len(hotels)]}",
                    "name": name,
                    "brand": brand,
                    "city": city,
                    "rate_before_tax_cents": rate,
                    "tax_cents": tax,
                }
            )
        files[f"scenarios/{scenario['facts']['scenario']}.json"] = json_text(scenario["facts"])
    files["airports.json"] = json_text(list(airports.values()))
    files["carriers.json"] = json_text(carriers)
    files["segments.json"] = json_text(list(segments.values()))
    files["itineraries.json"] = json_text(sorted(itineraries, key=lambda record: record["itinerary_id"]))
    files["travelers.json"] = json_text(travelers)
    files["hotels.json"] = json_text(sorted(hotels, key=lambda record: record["hotel_id"]))
    return files


def main():
    for relative, text in build().items():
        (DATA / relative).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
