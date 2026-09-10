"""Randvoorwaarde §2.2 en §2.9: regels zijn data, lijsten zijn niet gesloten.

Deze tests bewijzen wat de nultest wil bewijzen: dat er niets inhoudelijks in de
code zit. Ze doen dat niet door de code te lezen, maar door de data te veranderen
en te kijken of het gedrag meebeweegt.
"""

from __future__ import annotations

import pytest

from bewijsmotor.db.model import LOOKUP_KLASSEN
from bewijsmotor.db.registry import maak_engine, maak_schema, maak_sessiefabriek
from bewijsmotor.fouten import OnbekendeLookupwaarde
from bewijsmotor.labels import Schaal
from bewijsmotor.motor.engine import Motor
from conftest import lees_voorbeeld


def test_zonder_seed_verzint_de_motor_geen_schaal():
    """De sterkteschaal staat niet in de code. Zonder data is er geen schaal."""
    engine = maak_engine()
    maak_schema(engine)
    sessie = maak_sessiefabriek(engine)()
    with pytest.raises(OnbekendeLookupwaarde, match="schaal is leeg"):
        Schaal.uit_db(sessie)
    sessie.close()


def test_een_nieuw_premissetype_werkt_zonder_codewijziging(sessie, motor):
    """De typenlijst mag niet gesloten zijn. Een rij toevoegen volstaat."""
    invoer = lees_voorbeeld("nultest_zwakste_schakel.json")
    invoer["premises"][0]["type"] = "juridische_precedentbundel"

    with pytest.raises(OnbekendeLookupwaarde, match="juridische_precedentbundel"):
        motor.beoordeel(invoer, actor="test")

    sessie.rollback()
    sessie.add(
        LOOKUP_KLASSEN["premise_type"](
            key="juridische_precedentbundel",
            label_nl="juridische precedentbundel",
            label_en="body of legal precedent",
            omschrijving="door de gebruiker toegevoegd, zonder codewijziging",
        )
    )
    sessie.flush()

    verse_motor = Motor(sessie)
    uitvoer = verse_motor.beoordeel(invoer, actor="test")
    knoop = uitvoer["beoordelingen"][0]["chain"]["bewijslijnen"][0]["premissen"][0]
    assert knoop["type"] == "juridische_precedentbundel"


def test_een_extra_sterktelabel_verandert_het_rekenen_zonder_codewijziging(sessie):
    """De schaal is data. Voeg een trede toe en de ordening beweegt mee."""
    schaal_voor = Schaal.uit_db(sessie)
    assert schaal_voor.oplopend == (
        "undetermined",
        "weak",
        "probable",
        "strong",
        "certain",
    )

    sessie.add(
        LOOKUP_KLASSEN["strength_label"](
            key="zeer_waarschijnlijk",
            label_nl="zeer waarschijnlijk",
            label_en="highly probable",
            rangorde=25,
            omschrijving="tussentrede, door de gebruiker toegevoegd",
        )
    )
    sessie.execute(
        LOOKUP_KLASSEN["strength_label"]
        .__table__.update()
        .where(LOOKUP_KLASSEN["strength_label"].key == "strong")
        .values(rangorde=30)
    )
    sessie.execute(
        LOOKUP_KLASSEN["strength_label"]
        .__table__.update()
        .where(LOOKUP_KLASSEN["strength_label"].key == "certain")
        .values(rangorde=40)
    )
    sessie.flush()

    schaal_na = Schaal.uit_db(sessie)
    assert schaal_na.oplopend == (
        "undetermined",
        "weak",
        "probable",
        "zeer_waarschijnlijk",
        "strong",
        "certain",
    )
    assert schaal_na.minimum(["strong", "zeer_waarschijnlijk"]) == "zeer_waarschijnlijk"
    assert schaal_na.boven("probable")[0] == "zeer_waarschijnlijk"


def test_de_kernregel_achter_een_drogreden_is_data(sessie, motor):
    """Welke kernregel een bevinding draagt, staat in de lookup, niet in code."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_drogredenen.json"), actor="test")
    beoordeling = next(b for b in uitvoer["beoordelingen"] if b["claim_ref"] == "c_bc")
    assert beoordeling["fallacies"][0]["kernregel"] == "vorm_versus_waarheid"

    sessie.execute(
        LOOKUP_KLASSEN["fallacy_type"]
        .__table__.update()
        .where(LOOKUP_KLASSEN["fallacy_type"].key == "affirming_the_consequent")
        .values(kernregel="oordeel_vereist_begrip")
    )
    sessie.flush()

    opnieuw = Motor(sessie).beoordeel(lees_voorbeeld("nultest_drogredenen.json"), actor="test")
    beoordeling = next(b for b in opnieuw["beoordelingen"] if b["claim_ref"] == "c_bc")
    assert beoordeling["fallacies"][0]["kernregel"] == "oordeel_vereist_begrip"


def test_een_onbekende_waarde_wordt_geweigerd_met_uitleg(motor):
    invoer = lees_voorbeeld("nultest_zwakste_schakel.json")
    invoer["premises"][0]["provenance"]["kind"] = "gedroomd"
    with pytest.raises(OnbekendeLookupwaarde) as fout:
        motor.beoordeel(invoer, actor="test")
    melding = str(fout.value)
    assert "gedroomd" in melding
    assert "provenance_kind" in melding
    assert "Voeg een rij toe" in melding


def test_hernoemen_van_een_sleutel_waarop_de_motor_steunt_wordt_gemeld(sessie):
    """Regels zijn data, maar de motor noemt sommige waarden bij naam.

    Wordt zo'n rij hernoemd of op inactief gezet, dan zou de bijbehorende regel
    stilzwijgend ophouden te werken. Dat hoort een melding te zijn.
    """
    sessie.execute(
        LOOKUP_KLASSEN["critical_question_status"]
        .__table__.update()
        .where(LOOKUP_KLASSEN["critical_question_status"].key == "failed")
        .values(actief=False)
    )
    sessie.flush()
    with pytest.raises(OnbekendeLookupwaarde, match="failed"):
        Motor(sessie)
    sessie.rollback()


def test_profiel_zonder_bewijslastveld_wordt_geweigerd(sessie):
    """B1 noemt een standaard, maar die hoort in het profielrecord te staan."""
    from bewijsmotor.db.registry import laad_profiel
    from bewijsmotor.fouten import InvoerFout

    with pytest.raises(InvoerFout, match="burden_allocation"):
        laad_profiel(
            sessie,
            {
                "name": "zonder_bewijslast",
                "version": "0.1.0",
                "competence_levels": [{"name": "unrestricted"}],
            },
        )
    sessie.rollback()


def test_profiel_met_qawaid_wordt_niet_stil_genegeerd(sessie):
    from bewijsmotor.db.registry import laad_profiel
    from bewijsmotor.fouten import InvoerFout

    with pytest.raises(InvoerFout, match="regellaag wordt in fase 2 gebouwd"):
        laad_profiel(
            sessie,
            {
                "name": "met_qawaid",
                "version": "0.1.0",
                "burden_allocation": "claimant",
                "qaida_set": ["een_regel"],
                "competence_levels": [{"name": "unrestricted"}],
            },
        )
    sessie.rollback()
