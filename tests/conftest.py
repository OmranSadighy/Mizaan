"""Gemeenschappelijke opzet voor de tests.

Elke test begint met een verse database, de seed geladen, nul qawa'id en het
lege profiel. Dat is precies de situatie die de nultest voorschrijft.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from bewijsmotor.db.model import Profile, ProfilePremiseType, ProfileQaida, Qaida
from bewijsmotor.db.registry import laad_seed, maak_engine, maak_schema, maak_sessiefabriek
from bewijsmotor.motor.engine import Motor

WORTEL = Path(__file__).resolve().parents[1]
VOORBEELDEN = WORTEL / "voorbeelden"


@pytest.fixture
def engine():
    motor_engine = maak_engine()
    maak_schema(motor_engine)
    fabriek = maak_sessiefabriek(motor_engine)
    sessie = fabriek()
    laad_seed(sessie)
    sessie.commit()
    sessie.close()
    return motor_engine


@pytest.fixture
def sessie(engine):
    fabriek = maak_sessiefabriek(engine)
    huidige = fabriek()
    try:
        yield huidige
        huidige.commit()
    finally:
        huidige.close()


@pytest.fixture
def motor(sessie) -> Motor:
    return Motor(sessie)


@pytest.fixture
def leeg_profiel_is_leeg(sessie):
    """Bewijst de uitgangssituatie van de nultest: nul qawa'id, leeg profiel."""
    profiel = sessie.execute(select(Profile).where(Profile.name == "leeg")).scalars().one()
    assert sessie.execute(select(func.count()).select_from(Qaida)).scalar_one() == 0
    assert (
        sessie.execute(
            select(func.count())
            .select_from(ProfileQaida)
            .where(ProfileQaida.profile_id == profiel.id)
        ).scalar_one()
        == 0
    )
    assert (
        sessie.execute(
            select(func.count())
            .select_from(ProfilePremiseType)
            .where(ProfilePremiseType.profile_id == profiel.id)
        ).scalar_one()
        == 0
    )
    assert profiel.conflict_order == []
    assert profiel.figurative_reading_permitted is None
    return profiel


def lees_voorbeeld(naam: str) -> dict:
    return json.loads((VOORBEELDEN / naam).read_text(encoding="utf-8"))


def wandel(waarde, pad="$"):
    """Loop elke waarde in een geneste structuur langs, met haar pad."""
    yield pad, waarde
    if isinstance(waarde, dict):
        for sleutel, deel in waarde.items():
            yield from wandel(deel, f"{pad}.{sleutel}")
    elif isinstance(waarde, list):
        for nummer, deel in enumerate(waarde):
            yield from wandel(deel, f"{pad}[{nummer}]")
