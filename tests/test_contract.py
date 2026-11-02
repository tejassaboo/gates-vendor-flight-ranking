"""Structured input and structured output: every contract field is typed and described, every policy fact
reaches the agent in a typed field (never only in prose), and nothing the verifier grades is free text."""

import dataclasses
import typing
from enum import Enum

import contract
from contract import Airport, BookableCabin, Cabin, Carrier, GatesBookingOutput, Hotel, Itinerary, Segment

CONTRACT_CLASSES = [
    value
    for value in vars(contract).values()
    if isinstance(value, type) and dataclasses.is_dataclass(value) and value.__module__ == contract.__name__
]


def annotated_fields(cls):
    """(name, type, description) for every field, from the class's Annotated hints."""
    hints = typing.get_type_hints(cls, include_extras=True)
    for field in dataclasses.fields(cls):
        hint = hints[field.name]
        assert typing.get_origin(hint) is typing.Annotated, f"{cls.__name__}.{field.name} is not Annotated"
        base, *metadata = typing.get_args(hint)
        yield field.name, base, metadata[0]


def test_every_field_is_annotated_with_a_description() -> None:
    assert len(CONTRACT_CLASSES) >= 12
    for cls in CONTRACT_CLASSES:
        for name, _, description in annotated_fields(cls):
            assert isinstance(description, str) and description.strip(), f"{cls.__name__}.{name}"


def test_every_policy_fact_reaches_the_agent_in_a_typed_field() -> None:
    airport = {name: base for name, base, _ in annotated_fields(Airport)}
    carrier = {name: base for name, base, _ in annotated_fields(Carrier)}
    segment = {name: base for name, base, _ in annotated_fields(Segment)}
    itinerary = {name: base for name, base, _ in annotated_fields(Itinerary)}
    hotel = {name: base for name, base, _ in annotated_fields(Hotel)}
    assert airport["us_50_states_dc"] is bool  # domestic vs international
    assert carrier["preferred"] is bool  # ranking key 2
    assert segment["in_air_minutes"] is int  # the over-300-minute cabin rule
    assert segment["depart_local"] is str  # the late-departure window, YYYY-MM-DDTHH:MM origin local
    assert itinerary["fares_cents"] == dict[Cabin, int | None]
    assert hotel["rate_before_tax_cents"] is int and hotel["tax_cents"] is int  # the before-tax city cap


def test_the_graded_output_has_no_free_text() -> None:
    fields = {name: base for name, base, _ in annotated_fields(GatesBookingOutput)}
    assert fields == {
        "ranked_itinerary_ids": list[str],  # inventory ids, checked against the fixtures
        "selected_itinerary_id": str,
        "allowed_cabin": BookableCabin,
        "hotel_id": str,
    }
    assert issubclass(BookableCabin, Enum) and "first" not in {member.value for member in BookableCabin}


def test_dates_minutes_cents_nulls_and_orderings_are_stated() -> None:
    for cls in CONTRACT_CLASSES:
        for name, base, description in annotated_fields(cls):
            where = f"{cls.__name__}.{name}"
            if name.endswith(("_date", "_local", "_utc")) or name == "date":
                assert "YYYY-MM-DD" in description, where
            if name.endswith("_cents"):
                assert "cents" in description, where
            if name.endswith("_minutes"):
                assert "minutes" in description, where
            if "None" in repr(base):
                assert "null" in description, f"{where} does not say what null means"
            if typing.get_origin(base) is list and name != "ranked_itinerary_ids":
                assert any(word in description for word in ("by ", "order")), f"{where} does not state its order"
