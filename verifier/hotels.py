from .checks import DATA, UNEXPECTED, compared, plain, result
from .rules import hotels_view, load_gates_world


def verify_input(value):
    try:
        city = plain(value)["city"]
        if not city.strip():
            return result(False, "city must name a city")
        return result(True, "input is valid")
    except UNEXPECTED as error:
        return result(False, f"input is invalid: {error}")


def verify_output(input_value, output_value, workspace):
    try:
        wanted = hotels_view(load_gates_world(DATA), plain(input_value)["city"])
        return compared("get_hotels", plain(output_value), wanted)
    except UNEXPECTED as error:
        return result(False, f"verifier-error: {error!r}")
