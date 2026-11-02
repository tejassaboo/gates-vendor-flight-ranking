from slimconfig import build_output

from contract import SearchInput, SearchOutput
from plugin.fixtures import world
from plugin.rules import search_view
from plugin.world import IATA, day_number


def search_itineraries(given: SearchInput) -> SearchOutput:
    """Every itinerary from the origin to the destination on the date, with the carriers' preferred flag.
    It ranks nothing and applies no cabin rule."""
    airports = world()["airports"]
    for code in (given.origin, given.destination):
        if not IATA.fullmatch(code) or code not in airports:
            raise ValueError(f"{code!r} is not an airport in this inventory")
    if given.origin == given.destination:
        raise ValueError("origin and destination must differ")
    day_number(given.date)
    return build_output(search_view(world(), given.origin, given.destination, given.date), SearchOutput)
