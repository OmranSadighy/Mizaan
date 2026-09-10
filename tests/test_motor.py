"""Rekenregels van de motor die de nultest niet rechtstreeks noemt."""

from __future__ import annotations

import pytest

from bewijsmotor.fouten import InvoerFout, OngedefinieerdeVerwijzing
from conftest import lees_voorbeeld


def _basis() -> dict:
    return {
        "schema_version": "1.0.0",
        "submission": {"id": "motortest"},
        "claims": [{"id": "c1", "text": "De conclusie.", "form": {"kind": "atomic", "term": "q"}}],
        "premises": [
            {
                "id": "p1",
                "text": "Het feit.",
                "type": "sense_observation",
                "provenance": {"kind": "submitted_by_user"},
                "citation": {"source_ref": "Bron", "verification_status": "verified"},
                "thubut": {"label": "certain", "rationale": "handmatig: vastgesteld"},
                "form": {"kind": "atomic", "term": "p"},
            },
            {
                "id": "p2",
                "text": "De brug.",
                "type": "rational_intuition",
                "provenance": {"kind": "submitted_by_user"},
                "citation": {"source_ref": "Bron", "verification_status": "verified"},
                "thubut": {"label": "certain", "rationale": "handmatig: vastgesteld"},
                "form": {
                    "kind": "conditional",
                    "antecedent": {"kind": "atomic", "term": "p"},
                    "consequent": {"kind": "atomic", "term": "q"},
                },
            },
        ],
        "inferences": [{"id": "i1", "from": ["p1", "p2"], "to": "c1", "scheme": "deductive"}],
    }


def test_onbeantwoorde_kritische_vraag_verlaagt_niets(motor):
    invoer = _basis()
    invoer["inferences"][0]["critical_questions"] = [
        {"question": "Is dit werkelijk zo?", "status": "unanswered", "effect": "undercut"}
    ]
    beoordeling = motor.beoordeel(invoer, actor="test")["beoordelingen"][0]
    assert beoordeling["probative_force"]["label"] == "certain"
    assert any(v["status"] == "unanswered" for v in beoordeling["open_critical_questions"])


def test_gefaalde_kritische_vraag_plafonneert_op_onbepaald(motor):
    """Interim-regel: in fase 2 neemt de nederlaaggraaf deze rol over."""
    invoer = _basis()
    invoer["inferences"][0]["critical_questions"] = [
        {"question": "Is dit werkelijk zo?", "status": "failed", "effect": "undercut"}
    ]
    beoordeling = motor.beoordeel(invoer, actor="test")["beoordelingen"][0]
    assert beoordeling["probative_force"]["label"] == "undetermined"
    stap = beoordeling["chain"]["bewijslijnen"][0]["stapsterkte"]
    assert stap["label"] == "undetermined"
    assert "gefaald" in stap["rationale"]
    assert "Interim-regel" in stap["rationale"]


def test_formele_toets_gaat_voor_een_aangeleverd_label(motor):
    invoer = _basis()
    invoer["inferences"][0]["strength"] = {
        "label": "weak",
        "rationale": "handmatig: de indiener schatte de stap laag in",
    }
    beoordeling = motor.beoordeel(invoer, actor="test")["beoordelingen"][0]
    stap = beoordeling["chain"]["bewijslijnen"][0]["stapsterkte"]
    assert stap["label"] == "certain"
    assert stap["herkomst"] == "formeel"
    assert "de formele toets gaat daarvoor" in stap["rationale"]


def test_aangeleverd_label_geldt_als_de_vorm_niet_toetsbaar_is(motor):
    invoer = _basis()
    for premisse in invoer["premises"]:
        premisse.pop("form")
    invoer["claims"][0].pop("form")
    invoer["inferences"][0]["scheme"] = "expert_opinion"
    invoer["inferences"][0]["strength"] = {
        "label": "probable",
        "rationale": "handmatig: de deskundige is gezaghebbend maar niet doorslaggevend",
    }
    beoordeling = motor.beoordeel(invoer, actor="test")["beoordelingen"][0]
    stap = beoordeling["chain"]["bewijslijnen"][0]["stapsterkte"]
    assert stap["label"] == "probable"
    assert stap["herkomst"] == "aangeleverd"
    # De basisvragen van het schema komen ongevraagd mee als openstaand.
    vragen = [v["vraag"] for v in beoordeling["open_critical_questions"]]
    assert any("deskundig" in vraag for vraag in vragen)


def test_zwakste_sub_premisse_werkt_door_naar_het_geheel(motor):
    """De zwakste-schakelregel werkt ook binnen een premisse."""
    invoer = _basis()
    invoer["premises"][0]["sub_premises"] = [
        {
            "id": "p1a",
            "text": "Dat het zo is overgeleverd.",
            "type": "transmitted_report",
            "provenance": {"kind": "submitted_by_user"},
            "citation": {"source_ref": "Bron A", "verification_status": "verified"},
            "thubut": {"label": "certain", "rationale": "handmatig: onbetwist"},
        },
        {
            "id": "p1b",
            "text": "Dat er een grondslag onder ligt.",
            "type": "consensus_claim",
            "provenance": {"kind": "submitted_by_user"},
            "citation": {"source_ref": "Bron B", "verification_status": "disputed"},
            "thubut": {"label": "weak", "rationale": "handmatig: de grondslag is betwist"},
        },
    ]
    beoordeling = motor.beoordeel(invoer, actor="test")["beoordelingen"][0]
    assert beoordeling["probative_force"]["label"] == "weak"
    assert beoordeling["weakest_element"]["ref"] == "p1b"


def test_claim_zonder_bewijslijn_is_onvoldoende_onderbouwd(motor):
    invoer = _basis()
    invoer["inferences"] = []
    beoordeling = motor.beoordeel(invoer, actor="test")["beoordelingen"][0]
    assert beoordeling["probative_force"]["label"] == "undetermined"
    assert beoordeling["insufficient_evidence"]["waarde"] is True
    assert "geen bewijslijn" in beoordeling["insufficient_evidence"]["uitleg"]


def test_verwijzing_naar_iets_ongedefinieerds_wordt_geweigerd(motor):
    invoer = _basis()
    invoer["inferences"][0]["from"] = ["p1", "bestaat_niet"]
    with pytest.raises(OngedefinieerdeVerwijzing, match="bestaat_niet"):
        motor.beoordeel(invoer, actor="test")
    assert OngedefinieerdeVerwijzing.kernregel == "oordeel_vereist_begrip"


def test_dubbele_verwijzing_wordt_geweigerd(motor):
    invoer = _basis()
    invoer["premises"].append(dict(invoer["premises"][0]))
    with pytest.raises(InvoerFout, match="meer dan één keer"):
        motor.beoordeel(invoer, actor="test")


def test_stap_zonder_premissen_wordt_geweigerd(motor):
    invoer = _basis()
    invoer["inferences"][0]["from"] = []
    with pytest.raises(InvoerFout, match="draagt niets"):
        motor.beoordeel(invoer, actor="test")


def test_kantelpunten_wijzen_beide_kanten_op(motor):
    beoordeling = motor.beoordeel(lees_voorbeeld("nultest_zwakste_schakel.json"), actor="test")[
        "beoordelingen"
    ][0]
    richtingen = {k["richting"] for k in beoordeling["tipping_points"]}
    assert richtingen == {"upward", "downward"}

    omhoog = next(k for k in beoordeling["tipping_points"] if k["richting"] == "upward")
    assert omhoog["element_ref"] == "p_zwak"
    assert omhoog["current_label"] == "weak"
    assert omhoog["change_needed"] == "probable"
    assert omhoog["would_flip_to"] == "probable"


def test_kantelpunt_noemt_de_kleinste_wijziging(motor):
    """Niet de grootste denkbare wijziging, maar de eerste die kantelt."""
    beoordeling = motor.beoordeel(lees_voorbeeld("nultest_zwakste_schakel.json"), actor="test")[
        "beoordelingen"
    ][0]
    omhoog = [k for k in beoordeling["tipping_points"] if k["richting"] == "upward"]
    assert all(k["change_needed"] != "certain" for k in omhoog)


def test_de_volgorde_van_de_invoer_verandert_de_uitkomst_niet(motor):
    """Invariantie: wissel de invoervolgorde, de labels blijven gelijk."""
    invoer = lees_voorbeeld("kalibratie_gebed.json")
    eerste = motor.beoordeel(invoer, actor="test")["beoordelingen"][0]

    omgekeerd = lees_voorbeeld("kalibratie_gebed.json")
    omgekeerd["premises"].reverse()
    omgekeerd["inferences"].reverse()
    tweede = motor.beoordeel(omgekeerd, actor="test")["beoordelingen"][0]

    assert eerste["probative_force"]["label"] == tweede["probative_force"]["label"]
    assert eerste["insufficient_evidence"]["waarde"] == tweede["insufficient_evidence"]["waarde"]
    assert {f["soort"] for f in eerste["fallacies"]} == {f["soort"] for f in tweede["fallacies"]}


def test_dezelfde_argumentvorm_krijgt_hetzelfde_label(motor):
    """Symmetrie: het etiket van de partij doet er niet toe."""

    def bouw(naam: str) -> dict:
        invoer = _basis()
        invoer["submission"]["id"] = naam
        invoer["claims"][0]["text"] = f"De conclusie volgens {naam}."
        for premisse in invoer["premises"]:
            premisse["text"] = f"{premisse['text']} Aangevoerd door {naam}."
        return invoer

    a = motor.beoordeel(bouw("partij A"), actor="test")["beoordelingen"][0]
    b = motor.beoordeel(bouw("partij B"), actor="test")["beoordelingen"][0]
    assert a["probative_force"]["label"] == b["probative_force"]["label"]
    assert a["weakest_element"]["ref"] == b["weakest_element"]["ref"]
