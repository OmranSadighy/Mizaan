"""De nultest uit fase 1.

Met nul qawa'id geladen en een leeg profiel moet de motor zeven dingen doen.
Faalt er een, dan zit de fout in de kern en wordt hij daar gerepareerd.

Het doel van deze test is te bewijzen dat er niets inhoudelijks in de code zit.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bewijsmotor.contract import verifieer, weiger_enkel_getal
from bewijsmotor.fouten import ContractSchending, EnkelGetalGeweigerd
from conftest import lees_voorbeeld, wandel


def test_1_draait_zonder_fout(motor, leeg_profiel_is_leeg):
    """Criterium 1: zonder fout draaien."""
    for naam in (
        "nultest_ontleding.json",
        "nultest_verzwegen_premisse.json",
        "nultest_zwakste_schakel.json",
        "nultest_drogredenen.json",
        "nultest_zonder_bron.json",
        "kalibratie_gebed.json",
    ):
        uitvoer = motor.beoordeel(lees_voorbeeld(naam), actor="nultest")
        assert uitvoer["beoordelingen"], f"{naam} leverde geen beoordeling op"


def test_2_ontleedt_in_claims_premissen_en_inferenties(motor, leeg_profiel_is_leeg):
    """Criterium 2: een gestructureerde invoer ontleden."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_ontleding.json"), actor="nultest")
    ontleding = uitvoer["ontleding"]

    assert [c["ref"] for c in ontleding["claims"]] == ["c_tussen", "c_eind"]
    assert [p["ref"] for p in ontleding["premissen"]] == [
        "p_meting",
        "p_brug1",
        "p_sub",
        "p_brug2",
    ]
    # Niet alleen de verwijzingen, maar de hele verbinding: een stap zonder
    # premissen zou anders als geldige ontleding doorgaan.
    assert {i["ref"]: (tuple(i["van"]), i["naar"]) for i in ontleding["inferenties"]} == {
        "i_tussen": (("p_meting", "p_brug1"), "c_tussen"),
        "i_eind": (("p_sub", "p_brug2"), "c_eind"),
    }

    # De keten loopt over twee claims heen: de zwakste schakel van de eindclaim
    # ligt in de subconclusie, niet in een van haar eigen premissen.
    eind = next(b for b in uitvoer["beoordelingen"] if b["claim_ref"] == "c_eind")
    assert eind["weakest_element"]["soort"] == "claim"
    assert eind["weakest_element"]["ref"] == "c_tussen"

    # De keten is uitklapbaar tot de bron.
    lijn = eind["chain"]["bewijslijnen"][0]
    bronnen = [p["citaat"]["source_ref"] for p in lijn["premissen"]]
    assert "Beleidskader doeltreffendheid, art. 2" in bronnen


def test_3_meldt_mogelijk_verzwegen_premisse(motor, leeg_profiel_is_leeg):
    """Criterium 3: een verzwegen premisse melden waar een inferentie niet sluit."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_verzwegen_premisse.json"), actor="nultest")

    vorm = next(b for b in uitvoer["beoordelingen"] if b["claim_ref"] == "c_vorm")
    via_vorm = [v for v in vorm["possible_unstated_premises"] if v["basis"] == "form_completion"]
    assert via_vorm, "geen voorstel via vormaanvulling"
    assert via_vorm[0]["voorstel"].startswith("mogelijk verzwegen premisse")
    assert "als onvoorwaardelijk_gebod, dan verplicht" in via_vorm[0]["voorstel"]

    term = next(b for b in uitvoer["beoordelingen"] if b["claim_ref"] == "c_term")
    via_term = [v for v in term["possible_unstated_premises"] if v["basis"] == "term_coverage"]
    assert via_term, "geen voorstel via termdekking"
    assert "kan_verrichten" in via_term[0]["voorstel"]

    # Een voorstel is een voorstel: het telt niet mee en heet nooit een gat.
    for beoordeling in uitvoer["beoordelingen"]:
        for voorstel in beoordeling["possible_unstated_premises"]:
            assert voorstel["voorgesteld_door"] == "engine"
            assert voorstel["bevestigd"] is False
            assert voorstel["telt_mee_in_de_sterkte"] is False
            assert voorstel["voorstel"].startswith("mogelijk verzwegen premisse")
            assert "toets:" in voorstel["rationale"]

    # De termdekkingstoets noemt zichzelf een heuristiek.
    assert "heuristiek" in via_term[0]["rationale"]


def test_4_wijst_de_zwakste_schakel_aan(motor, leeg_profiel_is_leeg):
    """Criterium 4: de zwakste schakel correct aanwijzen."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_zwakste_schakel.json"), actor="nultest")
    beoordeling = uitvoer["beoordelingen"][0]

    assert beoordeling["weakest_element"]["ref"] == "p_zwak"
    assert beoordeling["weakest_element"]["veld"] == "dalalah"
    assert beoordeling["weakest_element"]["label"] == "weak"
    # Het eindlabel is dat van de zwakste schakel, niet van het gemiddelde.
    assert beoordeling["probative_force"]["label"] == "weak"
    assert "zwakste_schakel" in {regel["key"] for regel in beoordeling["kernel_rules_applied"]}


@pytest.mark.parametrize(
    ("claim_ref", "verwacht"),
    [
        ("c_bc", "affirming_the_consequent"),
        ("c_oa", "denying_the_antecedent"),
        ("c_um", "undistributed_middle"),
        ("c_kring1", "circular_reasoning"),
        ("c_kring2", "circular_reasoning"),
    ],
)
def test_5_herkent_formele_drogredenen(motor, leeg_profiel_is_leeg, claim_ref, verwacht):
    """Criterium 5: de vier formele drogredenen herkennen."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_drogredenen.json"), actor="nultest")
    beoordeling = next(b for b in uitvoer["beoordelingen"] if b["claim_ref"] == claim_ref)
    soorten = [f["soort"] for f in beoordeling["fallacies"]]

    assert verwacht in soorten
    # Elke drogreden noemt de kernregel die haar draagt.
    for bevinding in beoordeling["fallacies"]:
        assert bevinding["kernregel"]
        assert bevinding["rationale"]
    # Geen dubbeltelling: één bevinding per soort per element.
    sleutels = [(f["soort"], f["element_ref"]) for f in beoordeling["fallacies"]]
    assert len(sleutels) == len(set(sleutels))


def test_5_gebroken_vorm_verlaagt_maar_een_keer(motor, leeg_profiel_is_leeg):
    """Een formeel ongeldige stap levert precies één bevinding en één effect."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_drogredenen.json"), actor="nultest")
    beoordeling = next(b for b in uitvoer["beoordelingen"] if b["claim_ref"] == "c_bc")
    lijn = beoordeling["chain"]["bewijslijnen"][0]

    vormvraag = next(v for v in lijn["kritische_vragen"] if v["sleutel"].endswith("#d1"))
    assert vormvraag["beantwoord_door_motor"] is True
    assert vormvraag["status"] == "failed"
    # De vraag die de motor zelf beantwoordde, telt niet nog eens mee.
    assert len(beoordeling["fallacies"]) == 1
    assert beoordeling["probative_force"]["label"] == "undetermined"


def test_6_onvoldoende_bewijs_bij_premisse_zonder_bron(motor, leeg_profiel_is_leeg):
    """Criterium 6: 'onvoldoende bewijs' als een premisse geen bron heeft."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_zonder_bron.json"), actor="nultest")
    beoordeling = uitvoer["beoordelingen"][0]

    assert beoordeling["insufficient_evidence"]["waarde"] is True
    assert "p_zonderbron" in beoordeling["insufficient_evidence"]["premissen_zonder_bron"]
    assert beoordeling["probative_force"]["label"] == "undetermined"

    # De handmatige score is genegeerd en dat wordt gemeld, niet verzwegen.
    knoop = next(
        p
        for p in beoordeling["chain"]["bewijslijnen"][0]["premissen"]
        if p["ref"] == "p_zonderbron"
    )
    assert knoop["aangeleverde_scores"]["thubut"]["label"] == "certain"
    assert knoop["genegeerde_scores"] == [{"veld": "thubut", "aangeleverd_label": "certain"}]
    assert knoop["berekende_sterkte"]["label"] == "undetermined"
    assert "geen bron" in knoop["berekende_sterkte"]["rationale"]

    # En het kantelpunt zegt wat eraan te doen is.
    bron_punten = [k for k in beoordeling["tipping_points"] if k["veld"] == "citation.source_ref"]
    assert bron_punten and bron_punten[0]["would_flip_to"] == "certain"


def test_7_weigert_een_enkel_getal(motor, leeg_profiel_is_leeg):
    """Criterium 7: weigeren een enkel getal te produceren."""
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="nultest")

    # a. Nergens in de uitvoer staat een getal.
    getallen = [
        (pad, waarde)
        for pad, waarde in wandel(uitvoer)
        if isinstance(waarde, (int, float)) and not isinstance(waarde, bool)
    ]
    assert getallen == [], f"uitvoer bevat getallen: {getallen[:5]}"

    # b. De contractcontrole slaat wél aan als er een getal in zou staan.
    with pytest.raises(ContractSchending):
        verifieer({"beoordeling": {"score": 73}})

    # c. Wie expliciet om één cijfer vraagt, krijgt een weigering met uitleg.
    with pytest.raises(EnkelGetalGeweigerd) as fout:
        weiger_enkel_getal("test")
    assert "geen enkel samenvattend cijfer" in str(fout.value)


def test_7_command_line_weigert_een_enkel_getal(tmp_path):
    """De weigering geldt ook op de buitenste laag."""
    bestand = tmp_path / "invoer.json"
    bestand.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "claims": [{"id": "c1", "text": "x"}],
                "premises": [{"id": "p1", "text": "y", "provenance": {"kind": "user_supplied"}}],
                "inferences": [{"id": "i1", "from": ["p1"], "to": "c1"}],
            }
        ),
        encoding="utf-8",
    )
    wortel = Path(__file__).resolve().parents[1]
    uitkomst = subprocess.run(
        [sys.executable, "-m", "bewijsmotor.cli", "beoordeel", str(bestand), "--enkel-getal"],
        capture_output=True,
        text=True,
        cwd=str(wortel),
        env={**os.environ, "PYTHONPATH": "src"},
        check=False,
    )
    assert uitkomst.returncode == 2
    assert "EnkelGetalGeweigerd" in uitkomst.stderr
    assert "geen enkel samenvattend cijfer" in uitkomst.stderr
