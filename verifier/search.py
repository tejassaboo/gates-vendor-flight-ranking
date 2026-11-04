from .checks import DATA, UNEXPECTED, compared, plain, result
from .rules import load_gates_world, search_view
from .world import IATA, day_number


def verify_input(value):
    try:
        given = plain(value)
        airports = load_gates_world(DATA)["airports"]
        for code in (given["origin"], given["destination"]):
            if not IATA.fullmatch(code):
                return result(False, f"{code!r} is not a three-letter IATA code")
            if code not in airports:
                return result(False, f"{code!r} is not an airport in this inventory")
        if given["origin"] == given["destination"]:
            return result(False, "origin and destination must differ")
        day_number(given["date"])
        return result(True, "input is valid")
    except UNEXPECTED as error:
        return result(False, f"input is invalid: {error}")


def verify_output(input_value, output_value, workspace):
    try:
        given = plain(input_value)
        wanted = search_view(load_gates_world(DATA), given["origin"], given["destination"], given["date"])
        return compared("search_itineraries", plain(output_value), wanted)
    except UNEXPECTED as error:
        return result(False, f"verifier-error: {error!r}")
