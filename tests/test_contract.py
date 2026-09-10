"""Het uitvoercontract: nooit één getal, altijd een rationale, altijd versies."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from bewijsmotor.contract import verifieer, zoek_getallen
from bewijsmotor.db.model import Assessment
from bewijsmotor.fouten import ContractSchending
from conftest import lees_voorbeeld, wandel

ALLE_VOORBEELDEN = [
    "nultest_ontleding.json",
    "nultest_verzwegen_premisse.json",
    "nultest_zwakste_schakel.json",
    "nultest_drogredenen.json",
    "nultest_zonder_bron.json",
    "kalibratie_gebed.json",
]


@pytest.mark.parametrize("naam", ALLE_VOORBEELDEN)
def test_geen_enkel_getal_in_de_uitvoer(motor, naam):
    uitvoer = motor.beoordeel(lees_voorbeeld(naam), actor="contract")
    assert zoek_getallen(uitvoer) == []


@pytest.mark.parametrize("naam", ALLE_VOORBEELDEN)
def test_elk_score_object_draagt_een_rationale(motor, naam):
    uitvoer = motor.beoordeel(lees_voorbeeld(naam), actor="contract")
    gezien = 0
    for pad, waarde in wandel(uitvoer):
        if not isinstance(waarde, dict) or "label" not in waarde:
            continue
        if "rationale" not in waarde and "computed_by" not in waarde:
            continue
        gezien += 1
        assert waarde.get("rationale", "").strip(), f"score zonder rationale op {pad}"
    assert gezien > 0


@pytest.mark.parametrize("naam", ALLE_VOORBEELDEN)
def test_elke_beoordeling_draagt_haar_versies(motor, naam):
    uitvoer = motor.beoordeel(lees_voorbeeld(naam), actor="contract")
    for beoordeling in uitvoer["beoordelingen"]:
        versies = beoordeling["versies"]
        assert set(versies) >= {"motor", "contract", "invoerschema", "profiel", "regelset"}
        for sleutel, waarde in versies.items():
            assert isinstance(waarde, str) and waarde, f"versie '{sleutel}' ontbreekt"
        assert beoordeling["profiel"]["versie"]
        assert beoordeling["competentieniveau"]


def test_alle_assen_zijn_aanwezig(motor):
    """§2.5: uitvoer bestaat altijd uit meerdere assen."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_zwakste_schakel.json"), actor="contract")
    beoordeling = uitvoer["beoordelingen"][0]
    for sleutel in (
        "probative_force",
        "dialectical_force",
        "falsifiability_exposure",
        "weakest_element",
        "open_critical_questions",
        "fallacies",
        "tipping_points",
        "insufficient_evidence",
        "possible_unstated_premises",
        "chain",
        "kernel_rules_applied",
        "voorbehouden",
    ):
        assert sleutel in beoordeling, f"as '{sleutel}' ontbreekt in de uitvoer"
    # Assen die fase 1 niet berekent, zeggen dat met zoveel woorden.
    assert beoordeling["dialectical_force"]["berekend"] is False
    assert beoordeling["falsifiability_exposure"]["beoordeeld"] is False
    assert beoordeling["falsifiability_exposure"]["toelichting"]


def test_de_contractcontrole_vangt_getallen_op_elke_plek():
    with pytest.raises(ContractSchending):
        verifieer({"a": {"b": [1]}})
    with pytest.raises(ContractSchending):
        verifieer({"score": 0.73})
    with pytest.raises(ContractSchending):
        verifieer({"per_claim": {1: "x"}})
    # Booleans zijn geen getallen.
    verifieer({"insufficient_evidence": True, "label": "weak"})


def test_het_opgeslagen_rapport_bevat_evenmin_een_getal(sessie, motor):
    motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="contract")
    sessie.flush()
    beoordeling = sessie.execute(select(Assessment)).scalars().one()
    opgeslagen = json.loads(json.dumps(beoordeling.rapport))
    assert zoek_getallen(opgeslagen) == []


def test_de_rapportage_is_uitklapbaar_tot_de_kernregel(motor):
    """Ook het redeneren van de motor zelf is naspeurbaar."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_drogredenen.json"), actor="contract")
    beoordeling = next(b for b in uitvoer["beoordelingen"] if b["claim_ref"] == "c_bc")
    regels = {regel["key"]: regel for regel in beoordeling["kernel_rules_applied"]}
    assert "vorm_versus_waarheid" in regels
    for regel in regels.values():
        assert regel["statement"].strip()
        assert regel["self_refutation_argument"].strip()
    for bevinding in beoordeling["fallacies"]:
        assert bevinding["kernregel"] in regels


def test_de_uitvoer_noemt_wat_fase_1_niet_doet(motor):
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="contract")
    voorbehouden = " ".join(uitvoer["beoordelingen"][0]["voorbehouden"])
    assert "geen waarheid" in voorbehouden
    assert "geen personen" in voorbehouden
    assert "taalmodel" in voorbehouden
    assert uitvoer["voortgebracht_door"] == "motor zonder taalmodel"
