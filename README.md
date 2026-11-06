# Gates Vendor Flight Ranking

**No affiliation with the Gates Foundation.**

A `nanoagent.plugin/v0001` plugin. An agent plays the foundation travel desk for one vendor trip, under a
toy handbook paraphrased from the Gates Foundation Vendor Travel & Expense Policy (effective 7/1/2024).
It ranks every candidate flight in the travel desk's priority order, states the highest cabin the policy
allows on the chosen flight, and picks the hotel. A deterministic Python verifier, with no LLM, checks
the answer against an oracle that it computes itself.

## Task

- **Input:** `ScenarioInput`, whose single field `scenario` names one of fifteen bundled vendor trip
  requests, for example `{"scenario": "boston-board-retreat"}`.
- **Tools:** the agent calls `get_trip_request`, then `search_itineraries` and `get_hotels` in one reply,
  then `submit`. That is three of the six hosted steps (four if the two searches go in separate replies).
- **Output:** `GatesBookingOutput`, with these fields:
  - `ranked_itinerary_ids`: every candidate, best first;
  - `selected_itinerary_id`: equal to `ranked_itinerary_ids[0]`;
  - `allowed_cabin`: economy, premium_economy or business (an Enum);
  - `hotel_id`.
- **Success:** `valid` is true only when all four fields equal the one answer the handbook's rules give,
  the ranking position by position. `score` gives partial credit for how much is right (see Verifier).

The handbook is `src/plugin/data/handbook.md`. It is also the task's `instructions` in
`nanoagent.yaml`, and a test keeps the two identical. It has the paraphrased in-scope rules, the
"Clarifications (toy rules)" G1–G12, the rules not in scope, and the step plan.

Every fact the answer depends on is a typed field: origin, destination, departure date and preferred
departure time come from `get_trip_request`; segments, minutes, fares and the preferred flag come from
`search_itineraries`; rates, taxes and brands come from `get_hotels`. `request_text` is only the vendor's
voice and its distractors. A test checks that the oracle gives the same answer without it.

Each scenario sets a trap. Every trip has 6 to 8 candidates, with several preferred nonstops to order by
fare and a cheaper non-preferred late flight to resist, and every city has 5 to 8 hotels, with a banned one
or an over-cap one cheaper than the answer and several compliant ones to choose among:

| Scenario | Trap | Expected ranking, selected first | Cabin | Hotel |
|---|---|---|---|---|
| `boston-board-retreat` | The 21:00 departure is not after 9pm (331 min). A 31200 fare tie is split by distance from 21:30 (21:01 before 20:55). The Four Seasons and The Charles Hotel (banned by name) are cheaper than the compliant hotel. | I973, I467, I278, I552, I812, I283, I316, I595 | premium_economy | H491 |
| `new-york-donor-briefing` | 21:01 and 318 min on the same flight. A 21:00 non-preferred nonstop is the cheapest of all. The New York City cap is 400, so a 365 hotel is allowed. | I984, I157, I220, I116, I419, I184, I174 | business | H265 |
| `honolulu-health-workshop` | Honolulu is domestic: a 6 h flight leaving 20:00 is not business. Taxes never count toward the cap; 30001 is one cent over the default. | I441, I270, I383, I384, I633, I499, I529 | premium_economy | H350 |
| `mexico-city-nutrition-summit` | A 301-min international flight wins a fare tie on departure time. The vendor asks for economy, but allowed_cabin is the policy's. | I923, I719, I393, I472, I512, I426, I681 | business | H896 |
| `mexico-city-lab-audit` | The selected flight is exactly 300 min, so economy. A 301-min flight ranks second. | I852, I115, I707, I486, I192, I863 | economy | H896 |
| `london-global-health-convening` | The four-key order puts the non-preferred nonstop above every connection. London cap: 47500 is allowed, 47501 is not. | I649, I718, I848, I290, I741, I721 | business | H712 |
| `washington-policy-roundtable` | 08:00 and 10:00 tie on fare and on distance from 09:00, so itinerary_id decides. D.C. cap 350, with a hotel exactly at it. | I702, I806, I188, I489, I836, I907, I774 | premium_economy | H940 |
| `nairobi-field-mission` | Preferred connections beat the cheaper ones the vendor's airline loyalty wants. A meal-cap distractor. | I671, I308, I235, I995, I577, I164 | business | H702 |
| `nashville-education-summit` | The two nonstops are not preferred but beat cheaper preferred connections. Dream Nashville is banned. | I271, I332, I913, I565, I487, I837 | premium_economy | H842 |
| `tampa-grantee-expo` | Only the Tampa Marriott Water Street is banned, not every Marriott. A checked-bag distractor. | I344, I376, I342, I142, I893, I361 | premium_economy | H957 |
| `seattle-headquarters-visit` | A 00:30 departure counts as after 9pm (345 min, so business). Seattle uses the 300 default. | I948, I496, I855, I922, I458, I339 | business | H828 |
| `miami-vector-lab-demo` | A 21:30 hop of 55 min, then a 345-min leg at 06:05: no single flight is both late and long. 30001 is one cent over. | I299, I747, I135, I341, I238, I750 | premium_economy | H700 |
| `los-angeles-media-screening` | From JFK. A 04:59 departure is in the late window (335 min, so business); its 05:00 twin ranks second. Two compliant hotels tie at 27400: the lower hotel_id. The Beverly Wilshire is banned. | I962, I870, I449, I802, I899, I246, I581, I709 | business | H394 |
| `toronto-immunization-forum` | From HNL, international, no nonstop. The 320-min HNL-LAX leg allows business although the international leg is 270 min. Toronto cap 300: 30000 is allowed, 30001 is not. | I692, I369, I815, I975, I846, I768, I255 | business | H606 |
| `denver-sanitation-forum` | From MIA. The selected flight departs 21:05 but flies exactly 300 min, so premium_economy; its 301-min twin ranks second. | I723, I421, I452, I949, I699, I682, I710, I726 | premium_economy | H658 |

`seattle-headquarters-visit`, `mexico-city-nutrition-summit`, `miami-vector-lab-demo` and
`toronto-immunization-forum` are the subtle traps. An over-literal clock reading, an over-cautious echo of
the vendor's own cabin request, a reading that tests only the first segment's departure, and a reading that
tests only the international segment each get them wrong.

The boundary pairs the agent faces are 300 vs 301 minutes (the two Mexico City trips, international, and
Denver, domestic and late), 21:00 vs 21:01 (Boston and New York), 00:30 (Seattle) and 04:59 vs 05:00
(Los Angeles) in the late window, 47500 vs 47501 cents in London, and 30000 vs 30001 cents in Toronto,
Honolulu and Miami. Trips start at SEA, HNL, PDX, JFK and MIA.

## Tools

| Tool | Does | Code |
|---|---|---|
| `get_trip_request` | Returns a scenario's trip request: the vendor's words, the vendor, origin and destination airports (with city and the 50-states-plus-DC flag), departure date and preferred departure time | `src/plugin/trip.py` |
| `search_itineraries` | Lists every itinerary from one origin to one destination on a date, with segments, local times, in-air minutes, fares per cabin in cents, and each carrier's `preferred` flag. It ranks nothing | `src/plugin/search.py` |
| `get_hotels` | Lists every hotel in a city with its brand, nightly rate before tax and tax, in cents. It applies no cap or ban | `src/plugin/hotels.py` |
| `compute_travel_desk_booking` | The answer key: the oracle (`rules.oracle`) over the bundled fixtures. It is the task's `reference`, never shown to the agent | `src/plugin/reference.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `rank-gates-vendor-trip` | Ranks a vendor's flights, states the allowed cabin and picks the hotel | `agent`, with `get_trip_request`, `search_itineraries` and `get_hotels`; reference `compute_travel_desk_booking` |

The runner is `agent`, not `decide`: a `decide` runner fills a list item by item, so a five-id ranking
alone would exceed the six hosted steps.

## Environment

- Offline and self-contained: `hosts: []`, an empty `.env`, `write: []`, and no clock. "Today" is each
  scenario's `booking_date`.
- The inventory: 15 scenarios, 101 itineraries, 89 hotels, 20 airports, 9 carriers.
- Fixtures are in `src/plugin/data/`:
  - `airports.json`
  - `carriers.json`
  - `segments.json`, with local times, UTC times and `in_air_minutes` precomputed
  - `itineraries.json`
  - `travelers.json`
  - `hotels.json`
  - `scenarios/<id>.json`, which holds facts only and never an answer
- Airlines, flight numbers, fares and hotels are fictional. The exceptions are the properties the policy
  itself names, used only to test the ban. All rates are synthetic.
- The seeded generator `src/plugin/tools_dev/generate.py` writes the fixtures. A test checks that it
  reproduces the committed files byte for byte. The seed only scatters the itinerary and hotel ids.
- The shared core `src/plugin/world.py` (fixture schema, dates and minutes, search) and
  `tools_dev/worldgen.py` are vendored unchanged from the project's shared core.
- `world.py` and the Gates oracle `rules.py` are byte-identical in `src/plugin/` and `verifier/`.
- Python 3.12 or later, with dependencies pinned by `uv.lock`.

## Verifier

`verifier/booking.py` reads the fixtures through `Path(__file__)` and computes the oracle with the shared
`rules.py`. It checks the submission in four ordered stages, and each check has a stable reason code. The
message names the first failing check, with the rule and the numbers behind it, and later stages are
skipped. Two examples:

- "cabin-correct: business instead of premium_economy: I973 is domestic: ...; NS 902 departs 21:00 (not after 21:00 nor before 05:00), 331 min > 300"
- "selected-correct: I115 ranks above I852 by key 5 (itinerary_id): tied on every other key, and itinerary_id I115 < I852"

The stages and their reason codes:

1. **Answer key:** `reference-matches-oracle`.
2. **Referential integrity:**
   - `ranked-ids-exist`
   - `ranked-ids-serve-trip`
   - `hotel-exists`
   - `hotel-in-destination`
3. **Internal consistency:**
   - `ranked-unique`
   - `ranked-complete`
   - `selected-is-first`
4. **Decision against the oracle:**
   - `selected-correct`
   - `ranking-correct`
   - `cabin-correct`
   - `hotel-not-banned`
   - `hotel-within-cap`
   - `hotel-correct`

How it scores and reports:

- `valid` is strict: true only when every constraint holds, and then the score is 1.0.
- Otherwise `score` is partial credit in [0, 1], computed in hundredths so the parts add up exactly:
  - selection, 0.30: `selected_itinerary_id` is the oracle's and heads the ranking (G8);
  - order, 0.30 × (positions that hold the oracle's id) / (candidates), and only when the ranking is
    exactly the candidate set, each once: a partial, padded or stray list earns no order share;
  - cabin, 0.20: `allowed_cabin` is the oracle's, and only when the selection is right, because the cabin
    is defined on the selected itinerary (a right cabin on a wrong flight is a coincidence);
  - hotel, 0.20: `hotel_id` is the oracle's.
  - A referential-integrity failure (an id outside the inventory or the trip, a hotel outside the
    destination city) caps the score at 0.50. A broken answer key or a verifier error scores 0.
  - Wrong is wrong in either direction: business instead of premium_economy and economy instead of
    premium_economy both lose the cabin share; a hotel one cent over the cap and a cheaper banned one both
    lose the hotel share. Positions 5 and 6 of 8 swapped score 0.92; a lazy one-id ranking 0.70 at most;
    an empty answer 0; another scenario's answer 0, or 0.20 when the two trips share a city and so a hotel.
  - `details.score_parts` reports the four shares and the cap.
- `details.constraints` lists every check with `id`, `ok`, `expected`, `actual` and `message`, as plain JSON.
- Shape errors never reach the verifier, because NanoAgent's `build_output` refuses them first. These
  include a wrong type, an unknown Enum value such as `first`, a missing or extra field, and `null`.
- The verifier is pure stdlib and never raises. An unexpected value, an unknown scenario, and an unknown
  task or tool id each become a `verifier-error` verdict.
- Every tool output is also checked against the fixtures (`verify_output`).

## Validation

`tests/` covers this matrix:

- correct, incorrect, missing and malformed outputs, with malformed cases as `build_output` rejections;
- every boundary: 300/301 minutes; 21:00/21:01, 00:30, 04:59/05:00; the same-segment rule; each ranking
  key against the next; a departure distance across midnight; a hotel at the cap and one cent over; a
  hotel tie by id; each of these also as a bundled scenario, except the across-midnight distance;
- every reason code reached by a hand-written broken answer in some scenario's case (the answer-key check
  `reference-matches-oracle` needs a broken key, which a dedicated test supplies);
- partial credit: each share, the integrity cap, symmetry at the boundaries, lazy and other-scenario
  answers near zero, and every broken variant below 1.0;
- uniqueness: a strict order, with the id tie-break used only where the case documents it;
- oracle == the hand-written `tests/cases/<scenario>.json`;
- independence from `request_text`;
- the `rules.py` and `world.py` identity checks, and handbook == `instructions`;
- the verifier returns a failed verdict, and never raises, for an unknown task or tool id, an unknown
  scenario and a garbage reference;
- fixture integrity, recomputing times with `zoneinfo`, and no trip date on a daylight-saving change;
- generator reproducibility;
- tool-output size, kept under about 1.5k tokens (the largest search is about 4.5k characters);
- a cross-policy sanity row shared with the sibling travel-policy plugins (a 360-minute leg, a 90-minute
  layover and a 420-minute leg on an international trip give business);
- a real MCP server round trip;
- a scripted, no-LLM agent written from the handbook alone, which reaches every gold answer within the
  step budget, while each broken variant fails with its reason code.

## Limitations

- **The ranking order is a toy rule.** The policy's priority sentence is unnumbered, and "non-stop routes
  booked with the foundation's preferred carriers" can be read as one combined key (three keys in all)
  or as two (four in all). We use four separate keys. The readings disagree on the selection in
  `nashville-education-summit` and on the order in `london-global-health-convening`.
- **The policy names no "after 9pm" window end.** "After 9:00pm" is read as later than 21:00 or earlier
  than 05:00 local. The 05:00 cutoff is our choice.
- **The late departure and the long duration must be on the same flight.** The policy does not say so,
  and this is our reading.
- **Key 3 ranks on the economy fare whatever cabin is allowed.** "The lowest fare available" is read as the
  economy fare of each itinerary, so that one ranking serves every cabin outcome. A desk booking business
  would compare business fares, and the two readings can disagree. In this inventory the premium-economy
  and business fares of each trip order the same way as the economy fares (a test-time scan, not a rule), so
  no bundled scenario turns on it; the economy reading is a toy choice, stated in G6.
- **Other gaps the policy leaves open:**
  - "domestic" is read as both ends in the 50 states plus D.C., so on an international trip every
    segment over 300 minutes allows business, even a domestic positioning leg
    (`toronto-immunization-forum` turns on this);
  - `allowed_cabin` is the policy's ceiling, whatever fares the itinerary sells (every bundled itinerary
    sells economy, premium economy and business);
  - premium economy on international flights of five hours or less is read as not allowed (the policy
    allows it only domestically, and "not expressly covered" is not reimbursable).
- **Seattle uses the USD 300 default.** The revision history mentions a Seattle lodging update, but no
  Seattle cap is listed.
- **The priority order binds only travel-desk bookings.** The toy assumes every trip goes through the
  desk, and it books the cheapest compliant hotel instead of the desk's foundation-rate hotels.
- **The data is synthetic.** Fares and rates are fictional, the inventory is fixed, and there are no
  code-shares. The San Francisco, Geneva, Paris and Tokyo caps are in the cap table but no scenario stays
  there, so they are unit-tested only.
- **Some policy rules are distractors only.** The meal cap and the first-bag rule appear in requests, but
  the output has no field for them.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions, tools, the rank-gates-vendor-trip task and its handbook instructions
├── contract.py      # typed inputs and outputs of every tool and the task (Enums, int minutes and cents)
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # empty: the plugin needs no environment variables
├── src/plugin/      # MCP server (__main__.py), tools, world.py (shared core), rules.py (oracle), fixtures
│   ├── data/        # handbook.md, the fixture JSON files and scenarios/
│   └── tools_dev/   # the seeded fixture generator (development only)
├── tests/           # verifier matrix, oracle cases, scripted agent, rules, tools, fixtures
├── ui/              # renderers.js (a boarding-pass card for GatesBookingOutput) and renderers.css
├── product/         # product.yaml and icon.svg
└── verifier/        # deterministic verifier: booking.py (task), trip_request.py, search.py, hotels.py, rules.py, world.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run python -m plugin.tools_dev.generate   # rewrite the fixtures; the tests then check them
```

To run the agent, use `nanoagent plugin agent config=agent.yaml home=<run folder>` with `arguments` set
to a JSON file such as `{"scenario": "boston-board-retreat"}`. It needs `OPENROUTER_API_KEY` in the
environment, not in this repo.
