"""Bevindingen die de motor los van de labels vastlegt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DrogredenBevinding:
    soort: str
    element_soort: str
    element_ref: str
    rationale: str
    kernregel: str


@dataclass(frozen=True)
class VerzwegenVoorstel:
    """Een mogelijk verzwegen premisse.

    Nadrukkelijk een voorstel. De motor stelt niet vast dat er iets ontbreekt;
    zij zegt welke toets zij heeft gedaan en wat daaruit volgt.
    """

    inferentie_ref: str
    voorstel: str
    vorm: dict[str, Any] | None
    basis: str
    rationale: str
    proposed_by: str = "engine"
    confirmed: bool = False
