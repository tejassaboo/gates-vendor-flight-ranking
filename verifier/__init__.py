"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import booking, hotels, search, trip_request

TOOLS = {
    Tool.GET_TRIP_REQUEST: trip_request,
    Tool.SEARCH_ITINERARIES: search,
    Tool.GET_HOTELS: hotels,
    Tool.COMPUTE_TRAVEL_DESK_BOOKING: booking,
}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.RANK_GATES_VENDOR_TRIP: booking.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
