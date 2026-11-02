from slimconfig import build_output

from contract import HotelsInput, HotelsOutput
from plugin.fixtures import world
from plugin.rules import hotels_view


def get_hotels(given: HotelsInput) -> HotelsOutput:
    """Every hotel in the city, with its nightly rate before tax and its tax. It applies no cap or ban."""
    cities = sorted({hotel["city"] for hotel in world()["hotels"].values()})
    if given.city not in cities:
        raise ValueError(f"{given.city!r} has no hotels in this inventory; cities: {', '.join(cities)}")
    return build_output(hotels_view(world(), given.city), HotelsOutput)
