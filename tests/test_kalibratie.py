"""De kalibratietest uit fase 1.

Het onderwerp is een vehikel. Wat hier getoetst wordt, is of een keten waarin
elke schakel handmatig als 'zeker' is aangeleverd en elke stap formeel sluit,
ook 'zeker' als uitkomst geeft. Faalt dit, dan deugt de motor niet.

Dit is het enige soort test waarbij een vooraf bekend antwoord legitiem is.
"""

from __future__ import annotations

from conftest import lees_voorbeeld


def test_kalibratie_landt_bovenaan_de_schaal(motor, leeg_profiel_is_leeg):
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="kalibratie")
    beoordeling = uitvoer["beoordelingen"][0]

    assert beoordeling["claim_ref"] == "c_gebed"
    assert beoordeling["probative_force"]["label"] == "certain"
    assert beoordeling["probative_force"]["label_nl"] == "zeker"
    assert beoordeling["insufficient_evidence"]["waarde"] is False
    assert beoordeling["fallacies"] == []
    assert beoordeling["open_critical_questions"] == []
    assert beoordeling["possible_unstated_premises"] == []


def test_kalibratie_elke_lijn_sluit_afzonderlijk(motor, leeg_profiel_is_leeg):
    """Drie onafhankelijke bewijslijnen, elk formeel geldig en elk zeker."""
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="kalibratie")
    lijnen = uitvoer["beoordelingen"][0]["chain"]["bewijslijnen"]

    assert {lijn["inferentie_ref"] for lijn in lijnen} == {"i_koran", "i_hadith", "i_ijma"}
    for lijn in lijnen:
        assert lijn["vormtoets"]["status"] == "valid"
        assert lijn["stapsterkte"]["label"] == "certain"
        assert lijn["stapsterkte"]["herkomst"] == "formeel"
        assert lijn["lijnsterkte"]["label"] == "certain"
    assert sum(1 for lijn in lijnen if lijn["is_bepalende_lijn"]) == 1


def test_kalibratie_maximum_over_lijnen_met_reden(motor, leeg_profiel_is_leeg):
    """Een slechte lijn naast een sluitende lijn maakt de claim niet zwakker."""
    invoer = lees_voorbeeld("kalibratie_gebed.json")
    invoer["premises"].append(
        {
            "id": "p_zwakke_lijn",
            "text": "Een losse, zwak onderbouwde aanwijzing.",
            "type": "transmitted_report",
            "provenance": {"kind": "submitted_by_user"},
            "citation": {
                "source_ref": "Onbekende verzameling, zonder keten",
                "verification_status": "disputed",
            },
            "thubut": {"label": "weak", "rationale": "handmatig ingevoerd: de keten is onbekend"},
            "form": {"kind": "atomic", "term": "losse_aanwijzing"},
        }
    )
    invoer["premises"].append(
        {
            "id": "p_zwakke_brug",
            "text": "Een losse aanwijzing volstaat om de verplichting vast te stellen.",
            "type": "rational_intuition",
            "provenance": {"kind": "submitted_by_user"},
            "citation": {"source_ref": "Aangenomen regel", "verification_status": "unverified"},
            "thubut": {
                "label": "weak",
                "rationale": "handmatig ingevoerd: als losse aanname aangeleverd",
            },
            "form": {
                "kind": "conditional",
                "antecedent": {"kind": "atomic", "term": "losse_aanwijzing"},
                "consequent": {"kind": "atomic", "term": "gebed_is_verplicht"},
            },
        }
    )
    invoer["inferences"].append(
        {
            "id": "i_zwak",
            "from": ["p_zwakke_lijn", "p_zwakke_brug"],
            "to": "c_gebed",
            "scheme": "deductive",
        }
    )

    uitvoer = motor.beoordeel(invoer, actor="kalibratie")
    beoordeling = uitvoer["beoordelingen"][0]

    assert beoordeling["probative_force"]["label"] == "certain"
    rationale = beoordeling["probative_force"]["rationale"]
    assert "maximum" in rationale
    assert "niet zwakker geworden" in rationale
    zwakke_lijn = next(
        lijn for lijn in beoordeling["chain"]["bewijslijnen"] if lijn["inferentie_ref"] == "i_zwak"
    )
    assert zwakke_lijn["lijnsterkte"]["label"] == "weak"
    assert zwakke_lijn["is_bepalende_lijn"] is False


def test_kalibratie_zonder_de_brugpremisse_sluit_de_stap_niet(motor, leeg_profiel_is_leeg):
    """De motor kent de stelregel niet; laat je haar weg, dan sluit de keten niet.

    Dit is de kern van de nultest: dat een onvoorwaardelijk gebod op verplichting
    duidt, is een stelregel met eigen bewijs. Zonder qawa'id moet zij als
    expliciete premisse in de invoer staan.
    """
    invoer = lees_voorbeeld("kalibratie_gebed.json")
    invoer["premises"] = [p for p in invoer["premises"] if p["id"] != "p_regel_gebod"]
    invoer["inferences"] = [i for i in invoer["inferences"] if i["id"] in {"i_koran"}]
    invoer["inferences"][0]["from"] = ["p_koran"]

    uitvoer = motor.beoordeel(invoer, actor="kalibratie")
    beoordeling = uitvoer["beoordelingen"][0]

    assert beoordeling["probative_force"]["label"] == "undetermined"
    voorstellen = [v["voorstel"] for v in beoordeling["possible_unstated_premises"]]
    assert any("gebed_is_verplicht" in v for v in voorstellen), voorstellen
