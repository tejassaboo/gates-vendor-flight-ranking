"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import booking, hotels, search, trip_request
from .checks import result

TOOLS = {
    Tool.GET_TRIP_REQUEST: trip_request,
    Tool.SEARCH_ITINERARIES: search,
    Tool.GET_HOTELS: hotels,
    Tool.COMPUTE_TRAVEL_DESK_BOOKING: booking,
}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.RANK_GATES_VENDOR_TRIP: booking.verify_task}


def verify_input(tool, value):
    try:
        module = TOOLS[Tool(tool)]
    except ValueError as error:  # an unknown tool id: a failed verdict, never an exception
        return result(False, f"verifier-error: {error}")
    return module.verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    try:
        module = TOOLS[Tool(tool)]
    except ValueError as error:
        return result(False, f"verifier-error: {error}")
    return module.verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    try:
        check = TASKS[Task(task)]
    except ValueError as error:
        return result(False, f"verifier-error: {error}")
    return check(arguments, output, reference, workspace)
