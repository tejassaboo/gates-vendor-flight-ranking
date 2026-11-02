from slimconfig import build_output

from contract import GatesBookingOutput, ScenarioInput
from plugin.fixtures import scenario, world
from plugin.rules import oracle


def compute_travel_desk_booking(given: ScenarioInput) -> GatesBookingOutput:
    """The answer key: the one correct ranking, cabin and hotel, from the handbook's rules over the fixtures."""
    return build_output(oracle(world(), scenario(given.scenario.value)), GatesBookingOutput)
