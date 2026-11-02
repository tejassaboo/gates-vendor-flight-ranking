"""The bundled fixtures under data/, loaded once per plugin process."""

from functools import cache
from pathlib import Path

from plugin.rules import load_gates_world
from plugin.world import load_scenario

DATA = Path(__file__).resolve().parent / "data"


@cache
def world():
    return load_gates_world(DATA)


def scenario(scenario_id):
    return load_scenario(DATA, scenario_id)
