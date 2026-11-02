"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    GET_TRIP_REQUEST = "get_trip_request"
    SEARCH_ITINERARIES = "search_itineraries"
    GET_HOTELS = "get_hotels"
    COMPUTE_TRAVEL_DESK_BOOKING = "compute_travel_desk_booking"


class Task(Enum):
    RANK_GATES_VENDOR_TRIP = "rank-gates-vendor-trip"


class GatesScenario(Enum):
    """One vendor trip request per member; its facts are bundled with the plugin."""

    BOSTON_BOARD_RETREAT = "boston-board-retreat"
    NEW_YORK_DONOR_BRIEFING = "new-york-donor-briefing"
    HONOLULU_HEALTH_WORKSHOP = "honolulu-health-workshop"
    MEXICO_CITY_NUTRITION_SUMMIT = "mexico-city-nutrition-summit"
    MEXICO_CITY_LAB_AUDIT = "mexico-city-lab-audit"
    LONDON_GLOBAL_HEALTH_CONVENING = "london-global-health-convening"
    WASHINGTON_POLICY_ROUNDTABLE = "washington-policy-roundtable"
    NAIROBI_FIELD_MISSION = "nairobi-field-mission"
    NASHVILLE_EDUCATION_SUMMIT = "nashville-education-summit"
    TAMPA_GRANTEE_EXPO = "tampa-grantee-expo"
    SEATTLE_HEADQUARTERS_VISIT = "seattle-headquarters-visit"
    MIAMI_VECTOR_LAB_DEMO = "miami-vector-lab-demo"


class Cabin(Enum):
    """The full cabin ladder, lowest first: the cabins a fare is sold in."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class BookableCabin(Enum):
    """The cabins the policy can ever allow: first class never."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"


@dataclass
class ScenarioInput(Output):
    scenario: Annotated[GatesScenario, "Which vendor trip request to work, e.g. boston-board-retreat"]


@dataclass
class Vendor(Output):
    traveler_id: Annotated[str, "Traveler id, e.g. V201"]
    name: Annotated[str, "Full name"]
    firm: Annotated[str, "The vendor firm under contract with the foundation"]
    base_point: Annotated[str, "Where the vendor is based, e.g. Seattle, WA"]


@dataclass
class Airport(Output):
    code: Annotated[str, "IATA code"]
    city: Annotated[str, "City, exactly as get_hotels names it"]
    country: Annotated[str, "ISO country code"]
    us_50_states_dc: Annotated[bool, "In one of the 50 US states or Washington D.C."]


@dataclass
class TripRequestOutput(Output):
    scenario: Annotated[GatesScenario, "The scenario this request belongs to"]
    request_text: Annotated[str, "The vendor's words; they may ask for things policy overrides"]
    booking_date: Annotated[str, "Today, the day the travel desk books, YYYY-MM-DD"]
    traveler: Annotated[Vendor, "Who travels"]
    origin: Annotated[Airport, "Where the trip starts"]
    destination: Annotated[Airport, "Where the trip goes; the vendor stays in its city"]
    departure_date: Annotated[str, "Outbound departure date, YYYY-MM-DD, origin local"]
    preferred_departure_local: Annotated[str, "Preferred departure, origin local time, YYYY-MM-DDTHH:MM"]


@dataclass
class SearchInput(Output):
    origin: Annotated[str, "IATA code to depart from"]
    destination: Annotated[str, "IATA code to arrive at"]
    date: Annotated[str, "Departure date, YYYY-MM-DD, origin local"]


@dataclass
class Segment(Output):
    flight: Annotated[str, "Flight number as sold, e.g. CW 488; its carrier is the marketing carrier"]
    marketing_carrier: Annotated[str, "Carrier whose flight number is sold"]
    operating_carrier: Annotated[str, "Carrier that flies the plane"]
    origin: Annotated[str, "IATA code"]
    destination: Annotated[str, "IATA code"]
    depart_local: Annotated[str, "YYYY-MM-DDTHH:MM, origin local time"]
    arrive_local: Annotated[str, "YYYY-MM-DDTHH:MM, destination local time"]
    in_air_minutes: Annotated[int, "This one flight's takeoff-to-landing minutes"]


@dataclass
class Itinerary(Output):
    itinerary_id: Annotated[str, "Itinerary id, e.g. I457"]
    segments: Annotated[list[Segment], "Flights in flying order; one segment means nonstop"]
    arrive_utc: Annotated[str, "Final landing in UTC, YYYY-MM-DDTHH:MMZ"]
    fares_cents: Annotated[dict[Cabin, int | None], "Ticket price per cabin in USD cents; null when not sold"]


@dataclass
class Carrier(Output):
    code: Annotated[str, "Two-letter carrier code"]
    name: Annotated[str, "Carrier name"]
    preferred: Annotated[bool, "One of the foundation's preferred carriers"]


@dataclass
class SearchOutput(Output):
    itineraries: Annotated[list[Itinerary], "Every itinerary from the origin to the destination on that date, by itinerary_id"]
    carriers: Annotated[list[Carrier], "Every carrier on those itineraries, by code"]


@dataclass
class HotelsInput(Output):
    city: Annotated[str, "City to stay in, exactly as the trip request's destination.city names it"]


@dataclass
class Hotel(Output):
    hotel_id: Annotated[str, "Hotel id, e.g. H512"]
    name: Annotated[str, "Property name"]
    brand: Annotated[str, "Hotel brand or chain; Independent when none"]
    city: Annotated[str, "City"]
    rate_before_tax_cents: Annotated[int, "Nightly room rate before taxes, USD cents"]
    tax_cents: Annotated[int, "Nightly taxes and fees on top of the rate, USD cents"]


@dataclass
class HotelsOutput(Output):
    city: Annotated[str, "The city searched"]
    hotels: Annotated[list[Hotel], "Every hotel in the city, by hotel_id"]


@dataclass
class GatesBookingOutput(Output):
    ranked_itinerary_ids: Annotated[
        list[str], "Every candidate itinerary id, each once, best first, in the travel desk's priority order"
    ]
    selected_itinerary_id: Annotated[str, "The itinerary to book: the first id of ranked_itinerary_ids"]
    allowed_cabin: Annotated[BookableCabin, "The highest cabin the policy allows on the selected itinerary"]
    hotel_id: Annotated[str, "The hotel to book in the destination city"]


TOOLS = {
    Tool.GET_TRIP_REQUEST: (ScenarioInput, TripRequestOutput),
    Tool.SEARCH_ITINERARIES: (SearchInput, SearchOutput),
    Tool.GET_HOTELS: (HotelsInput, HotelsOutput),
    Tool.COMPUTE_TRAVEL_DESK_BOOKING: (ScenarioInput, GatesBookingOutput),
}
TASKS = {Task.RANK_GATES_VENDOR_TRIP: (ScenarioInput, GatesBookingOutput)}
