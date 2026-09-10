"""Het profiel: leeg in fase 1, en onbepaald blijft onbepaald."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from bewijsmotor.db.model import KernelRule, Profile
from bewijsmotor.db.registry import haal_profiel, laad_profiel
from bewijsmotor.fouten import OnbekendeLookupwaarde, OnbepaaldeProfielinstelling
from bewijsmotor.motor.engine import profielinstelling


def test_het_lege_profiel_is_werkelijk_leeg(leeg_profiel_is_leeg):
    profiel = leeg_profiel_is_leeg
    assert profiel.name == "leeg"
    assert profiel.version
    assert profiel.burden_allocation == "claimant"


def test_onbepaalde_instelling_faalt_en_valt_niet_terug(sessie, leeg_profiel_is_leeg):
    """Elke standaardwaarde zou al een standpunt zijn."""
    with pytest.raises(OnbepaaldeProfielinstelling) as fout:
        profielinstelling(leeg_profiel_is_leeg, "figurative_reading_permitted")
    melding = str(fout.value)
    assert "figurative_reading_permitted" in melding
    assert "valt niet terug op een standaardwaarde" in melding


def test_een_ingesteld_veld_wordt_gewoon_gelezen(sessie):
    profiel = laad_profiel(
        sessie,
        {
            "name": "toetsprofiel",
            "version": "0.1.0",
            "figurative_reading_permitted": False,
            "burden_allocation": "departer_from_status_quo",
            "competence_levels": [{"name": "unrestricted"}],
        },
    )
    assert profielinstelling(profiel, "burden_allocation") == "departer_from_status_quo"
    assert profiel.figurative_reading_permitted is False


def test_bewijslast_is_een_profielinstelling_en_geen_kernregel(sessie, leeg_profiel_is_leeg):
    """B1: wélke allocatie geldt, hoort niet in de kern."""
    assert "burden_allocation" in {kolom.name for kolom in Profile.__table__.columns}
    kernteksten = " ".join(
        rij.statement_nl for rij in sessie.execute(select(KernelRule)).scalars()
    ).lower()
    for allocatie in ("claimant", "status quo", "departer"):
        assert allocatie not in kernteksten
    steunregel = sessie.get(KernelRule, "steun_en_bewijslast")
    assert "geen kernregel maar een profielinstelling" in steunregel.statement_nl


def test_onbekend_profiel_geeft_een_duidelijke_melding(sessie):
    with pytest.raises(OnbekendeLookupwaarde, match="bestaat niet"):
        haal_profiel(sessie, "hanafitisch")
