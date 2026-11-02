# Gates Foundation vendor travel: toy travel-desk handbook

Source: Bill & Melinda Gates Foundation, "Vendor Travel & Expense Policy", marked "Effective 7/1/2024" (https://docs.gatesfoundation.org/documents/travel%20and%20expense%20-%20vendor.pdf), read on 2026-11-02. This handbook is our own paraphrase for a toy task, not the official text. Where the two differ, this handbook governs the task. Airlines, flight numbers, fares and hotels are fictional except the properties the policy itself names; every rate is synthetic.

You act as the foundation travel desk for one vendor trip. You rank the candidate flights, say which cabin the policy allows on the chosen flight, and pick the hotel. Every rule below is applied to the structured fields the tools return.

## Policy rules (paraphrased)

1. Domestic flights are booked in economy; premium economy is also allowed.
2. A domestic flight that departs after 9:00pm and lasts more than five hours may be booked in business.
3. An international flight that lasts more than five hours may be booked in business.
4. The travel desk books itineraries in this order of importance: non-stop routes, the foundation's preferred carriers, the lowest fare available when booking, then the preferred departure date and time. These priorities override personal preferences and frequent-flyer considerations.
5. Lodging costs at most USD 300 per night before taxes, except: Washington D.C. 350; Boston, New York City and San Francisco 400; Geneva 400; Paris and Tokyo 450; London 475.
6. The foundation never reimburses any expense at these properties: any Four Seasons hotel or resort (including the Beverly Wilshire); The Charles Hotel in Cambridge, Massachusetts; the Dream Nashville Hotel; the Tampa Marriott Water Street.
7. Anything the policy does not expressly cover is not reimbursable.

## Clarifications (toy rules)

These settle every point where the real text is vague. The checker enforces exactly these.

- **G1 Domestic.** A trip is domestic when both origin.us_50_states_dc and destination.us_50_states_dc are true (the policy does not define it). Honolulu is therefore domestic. Connection airports do not matter.
- **G2 Flight duration.** "Flight duration" means one flight (segment), takeoff to landing: its in_air_minutes. Legs are never added and layovers never count. "More than five hours" means in_air_minutes greater than 300; exactly 300 does not qualify.
- **G3 After 9:00pm.** A segment departs "after 9:00pm" when its depart_local clock time (local at that segment's own origin airport) is later than 21:00 or earlier than 05:00. So 21:00 does not qualify; 21:01 to 23:59 and 00:00 to 04:59 (an overnight departure) qualify; 05:00 onward does not. The 05:00 cutoff is our choice; the policy names none. Words like "red-eye" or "basically 9pm" in a request change nothing.
- **G4 Allowed cabin.** On a domestic trip, business is allowed when at least one single segment both departs after 9:00pm (G3) and lasts more than 300 minutes (G2). Both conditions must hold for the same segment. Otherwise the highest allowed cabin is premium_economy. On an international trip, business is allowed when at least one segment lasts more than 300 minutes; otherwise the highest allowed cabin is economy, because the policy expressly allows premium economy only on domestic flights (rule 7). First class is never allowed. allowed_cabin is the highest cabin allowed on the selected itinerary, whatever cabin the vendor asks for, including when they ask for less, and whatever fares the itinerary sells: it is the policy's ceiling, not a fare lookup.
- **G5 Candidates.** The candidates are every itinerary that search_itineraries returns for the trip's origin, destination and departure_date. Rank all of them, each once.
- **G6 Ranking.** Sort the candidates by these keys, comparing a key only when all earlier keys tie:
  1. nonstop (exactly one segment) before connecting;
  2. preferred before not: an itinerary is preferred when the marketing carrier of every segment is a preferred carrier. The foundation's preferred carriers here are Cascade Airways (CW), Northstar Air (NS), Regent Airways (RG) and Tulip Blue (TB); search results flag them preferred: true;
  3. lower fares_cents.economy, whatever cabin is later allowed;
  4. smaller distance in minutes between the first segment's depart_local and preferred_departure_local (both on the origin airport's clock; compare full date and time, so 23:55 is 23h40m from 00:15 the same morning);
  5. lower itinerary_id, compared as text.
  The real sentence lists the priorities without numbering them, and "non-stop routes booked with the foundation's preferred carriers" could also be read as one combined first key (three keys in all). This handbook uses the four separate keys above.
- **G7 Whose preferences.** The vendor's wishes about airlines, loyalty programs, connections or cabins never change the ranking or the cabin. Requests about lounge passes, meals (the policy caps meals at USD 150 a day) or bags (the first checked bag is reimbursable) are outside this task's output and change nothing.
- **G8 Selection.** selected_itinerary_id is the first id of ranked_itinerary_ids.
- **G9 Hotel.** From get_hotels for destination.city, keep the hotels that are not banned (G11) and whose rate_before_tax_cents is at most the city's cap (G10). Book the one with the lowest rate_before_tax_cents; on a tie, the lower hotel_id. Taxes (tax_cents) never count toward the cap or the comparison.
- **G10 Caps, in cents.** Washington D.C. 35000; Boston, New York City, San Francisco and Geneva 40000; Paris and Tokyo 45000; London 47500; every other city 30000. A rate exactly at the cap is allowed; one cent over is not. The policy's revision history mentions a Seattle rate update, but its table lists no Seattle rate, so Seattle uses 30000.
- **G11 Banned properties.** A hotel is banned when its brand is Four Seasons, or its name is exactly Beverly Wilshire, The Charles Hotel, Dream Nashville Hotel or Tampa Marriott Water Street. Only these named properties are banned: other hotels of the same chains (another Marriott, for example) are fine.
- **G12 Facts.** The structured fields are the facts; never parse request_text for them. The request may ask for things policy overrides, so apply the policy, not the wish. in_air_minutes and local times are given, so never do timezone arithmetic.

## Rules not in scope

The following parts of the policy are deliberately ignored:

- choosing third-party providers;
- anti-corruption rules;
- the pre-trip price quotation for mixed foundation and personal travel;
- invoicing airfare after travel;
- cancellation fees;
- lost baggage;
- ground transportation, parking, mileage and rental cars;
- lodging folios and incidentals;
- the meal-sharing rules;
- visa, passport and immunization fees;
- equipment;
- the travel desk's foundation-rate hotels (this toy books the cheapest compliant hotel instead);
- the travel desk's car service and cancellations;
- invoice formats, the 60-day deadline and the USD 75 receipt rule;
- exceptions granted by the CFO;
- the return flight.

The priority order binds travel-desk bookings; this toy assumes every trip is booked by the travel desk.

## Step plan (submit by step 5)

You have 6 steps, each reply with tool calls costs one, and the last step may not call tools.

1. Call get_trip_request with the task's scenario.
2. In one reply, call search_itineraries with origin.code, destination.code and date = departure_date, and get_hotels with city = destination.city.
3. Apply G1–G12 and call submit with ranked_itinerary_ids (every candidate, best first), selected_itinerary_id, allowed_cabin and hotel_id.
