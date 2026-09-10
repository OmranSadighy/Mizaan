"""Toetst de nultest zelf: zou zij rood worden als de motor het fout deed?

Het doel van de nultest is te bewijzen dat er niets inhoudelijks in de code zit.
Een test die groen blijft bij een verkeerde motor bewijst niets. Deze tests
pinnen daarom niet alleen het goede gedrag vast, maar ook de afwezigheid van het
verkeerde: geen verzonnen drogredenen, geen voorstellen bij een sluitende stap,
geen 'onvoldoende bewijs' waar elke premisse een bron noemt, en een uitkomst die
niet met zichzelf in tegenspraak is.
"""

from __future__ import annotations

import json

import pytest

from bewijsmotor.fouten import ContractSchending
from bewijsmotor.motor import rapport as rapportmodule
from conftest import lees_voorbeeld, wandel


def test_minimum_binnen_een_lijn_is_geen_maximum(motor):
    """Zou de motor binnen een lijn het maximum nemen, dan werd dit rood."""
    uitvoer = motor.beoordeel(lees_voorbeeld("nultest_zwakste_schakel.json"), actor="scherpte")
    beoordeling = uitvoer["beoordelingen"][0]
    lijn = beoordeling["chain"]["bewijslijnen"][0]

    labels = {p["berekende_sterkte"]["label"] for p in lijn["premissen"]}
    assert labels == {"certain", "weak"}, "de opzet moet een sterke en een zwakke premisse hebben"
    assert lijn["stapsterkte"]["label"] == "certain"
    assert lijn["lijnsterkte"]["label"] == "weak", "binnen een lijn geldt het minimum"
    assert beoordeling["probative_force"]["label"] == "weak"


def test_de_uitkomst_spreekt_zichzelf_niet_tegen(motor):
    """Het eindlabel is het label van de aangewezen zwakste schakel."""
    for naam in (
        "nultest_zwakste_schakel.json",
        "nultest_ontleding.json",
        "kalibratie_gebed.json",
    ):
        uitvoer = motor.beoordeel(lees_voorbeeld(naam), actor="scherpte")
        for beoordeling in uitvoer["beoordelingen"]:
            zwakste = beoordeling["weakest_element"]
            if zwakste is None:
                continue
            assert beoordeling["probative_force"]["label"] == zwakste["label"], (
                f"{naam}/{beoordeling['claim_ref']}: het eindlabel wijkt af van de "
                "aangewezen zwakste schakel"
            )


def test_de_bepalende_lijn_draagt_het_eindlabel(motor):
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="scherpte")
    beoordeling = uitvoer["beoordelingen"][0]
    bepalend = [lijn for lijn in beoordeling["chain"]["bewijslijnen"] if lijn["is_bepalende_lijn"]]
    assert len(bepalend) == 1
    assert bepalend[0]["lijnsterkte"]["label"] == beoordeling["probative_force"]["label"]


def test_geen_verzonnen_drogredenen_bij_een_sluitende_keten(motor):
    """De motor mag niets melden wat zij niet heeft aangetroffen."""
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="scherpte")
    beoordeling = uitvoer["beoordelingen"][0]
    assert beoordeling["fallacies"] == []
    assert beoordeling["steunkring"]["gevonden"] is False
    assert beoordeling["steunkring"]["kringen_van_deze_claim"] == []


def test_geen_voorstel_voor_een_verzwegen_premisse_bij_een_sluitende_stap(motor):
    """Criterium 3 geldt 'waar een inferentie niet sluit', en alleen daar."""
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="scherpte")
    beoordeling = uitvoer["beoordelingen"][0]
    assert beoordeling["possible_unstated_premises"] == []
    for lijn in beoordeling["chain"]["bewijslijnen"]:
        assert lijn["vormtoets"]["status"] == "valid"


def test_termdekking_gaat_niet_los_op_een_geldige_stap(motor):
    """De heuristiek draait alleen als de vorm niets heeft kunnen vaststellen."""
    invoer = lees_voorbeeld("kalibratie_gebed.json")
    # Termen toevoegen die in geen premisse voorkomen; de vorm sluit nog steeds.
    invoer["claims"][0]["terms"] = ["gebed_is_verplicht", "term_die_nergens_staat"]
    uitvoer = motor.beoordeel(invoer, actor="scherpte")
    beoordeling = uitvoer["beoordelingen"][0]
    assert beoordeling["possible_unstated_premises"] == [], (
        "termdekking mag niet aanslaan op een stap waarvan de vorm sluit"
    )


def test_geen_onvoldoende_bewijs_waar_elke_premisse_een_bron_noemt(motor):
    """Criterium 6 mag geen vals alarm geven."""
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="scherpte")
    beoordeling = uitvoer["beoordelingen"][0]
    assert beoordeling["insufficient_evidence"]["waarde"] is False
    assert beoordeling["insufficient_evidence"]["premissen_zonder_bron"] == []


def test_bronloze_lijn_naast_een_sluitende_lijn_maakt_de_claim_niet_onvoldoende(motor):
    """Het gemengde geval: één lijn draagt niet, de andere wel."""
    invoer = lees_voorbeeld("kalibratie_gebed.json")
    invoer["premises"].append(
        {
            "id": "p_los",
            "text": "Een bewering zonder bron.",
            "type": "transmitted_report",
            "provenance": {"kind": "user_supplied"},
            "thubut": {"label": "certain", "rationale": "handmatig: zonder bron aangeleverd"},
            "form": {"kind": "atomic", "term": "gebed_is_verplicht"},
        }
    )
    invoer["inferences"].append(
        {"id": "i_los", "from": ["p_los"], "to": "c_gebed", "scheme": "deductive"}
    )
    beoordeling = motor.beoordeel(invoer, actor="scherpte")["beoordelingen"][0]

    assert beoordeling["probative_force"]["label"] == "certain"
    assert beoordeling["insufficient_evidence"]["waarde"] is False
    assert "p_los" in beoordeling["insufficient_evidence"]["premissen_zonder_bron"]
    assert "i_los" in beoordeling["insufficient_evidence"]["uitleg"]
    bepalend = next(
        lijn for lijn in beoordeling["chain"]["bewijslijnen"] if lijn["is_bepalende_lijn"]
    )
    assert bepalend["inferentie_ref"] != "i_los", (
        "een lijn met een premisse zonder bron mag de bepalende lijn niet zijn"
    )


def test_de_motor_weigert_zelf_wanneer_er_toch_een_getal_in_de_uitvoer_belandt(motor, monkeypatch):
    """Criterium 7 pint niet alleen de gelukkige weg vast.

    De contractcontrole zit in de motor, niet naast de motor. Belandt er door een
    latere wijziging toch een getal in de uitvoer, dan komt die uitvoer niet naar
    buiten.
    """
    echte_bouwer = rapportmodule.bouw_beoordeling

    def bouwer_met_getal(*args, **kwargs):
        beoordeling = echte_bouwer(*args, **kwargs)
        beoordeling["probative_force"]["gemakscijfer"] = 73
        return beoordeling

    monkeypatch.setattr("bewijsmotor.motor.engine.bouw_beoordeling", bouwer_met_getal)
    with pytest.raises(ContractSchending, match="bevat een getal"):
        motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="scherpte")


def test_de_uitkomst_hangt_niet_aan_de_woorden_van_het_onderwerp(motor):
    """De sterkste toets op 'geen inhoud in de code': hernoem alles.

    Elke term, elke tekst en elke verwijzing in de invoer krijgt een neutrale
    naam. Zou de motor ergens op de inhoud van het onderwerp reageren, dan
    verandert de uitkomst mee.
    """
    origineel = lees_voorbeeld("kalibratie_gebed.json")
    eerste = motor.beoordeel(origineel, actor="scherpte")["beoordelingen"][0]

    ruw = json.dumps(lees_voorbeeld("kalibratie_gebed.json"), ensure_ascii=False)
    woordenboek = {
        "gebed_is_verplicht": "x1",
        "onvoorwaardelijk_gebod_in_openbaring": "x2",
        "gebed_is_zuil": "x3",
        "consensus_over_verplichting": "x4",
    }
    for oud, nieuw in woordenboek.items():
        ruw = ruw.replace(oud, nieuw)
    hernoemd = json.loads(ruw)
    for claim in hernoemd["claims"]:
        claim["text"] = "propositie A"
    for nummer, premisse in enumerate(hernoemd["premises"]):
        premisse["text"] = f"bewering {nummer}"
        premisse["citation"]["source_ref"] = f"bron {nummer}"
        for veld in ("thubut", "dalalah"):
            if veld in premisse:
                premisse[veld]["rationale"] = "handmatig ingevoerd voor deze toets"
        premisse.pop("status", None)
    hernoemd["submission"]["id"] = "hernoemd"
    hernoemd["submission"]["title"] = "zonder onderwerp"

    tweede = motor.beoordeel(hernoemd, actor="scherpte")["beoordelingen"][0]

    assert tweede["probative_force"]["label"] == eerste["probative_force"]["label"]
    assert tweede["insufficient_evidence"]["waarde"] == eerste["insufficient_evidence"]["waarde"]
    assert [f["soort"] for f in tweede["fallacies"]] == [f["soort"] for f in eerste["fallacies"]]
    assert len(tweede["chain"]["bewijslijnen"]) == len(eerste["chain"]["bewijslijnen"])
    assert [lijn["vormtoets"]["status"] for lijn in tweede["chain"]["bewijslijnen"]] == [
        lijn["vormtoets"]["status"] for lijn in eerste["chain"]["bewijslijnen"]
    ]


def test_geen_eindcijfer_als_tekenreeks(motor):
    """Ook een cijfer vermomd als tekst hoort er niet te zijn."""
    uitvoer = motor.beoordeel(lees_voorbeeld("kalibratie_gebed.json"), actor="scherpte")
    verdacht = []
    for pad, waarde in wandel(uitvoer):
        if not isinstance(waarde, str):
            continue
        kaal = waarde.strip().rstrip("%").replace(",", ".")
        try:
            float(kaal)
        except ValueError:
            continue
        verdacht.append((pad, waarde))
    assert verdacht == [], f"tekenreeksen die als cijfer te lezen zijn: {verdacht}"


def _stap(premissetype: str, schema: str, status: dict | None = None) -> dict:
    """Dezelfde argumentvorm, met instelbare inhoudelijke velden."""
    premisse = {
        "id": "p1",
        "text": "Het feit.",
        "type": premissetype,
        "provenance": {"kind": "user_supplied"},
        "citation": {"source_ref": "Bron", "verification_status": "verified"},
        "thubut": {"label": "strong", "rationale": "handmatig: vastgesteld"},
        "form": {"kind": "atomic", "term": "p"},
    }
    if status is not None:
        premisse["status"] = status
    return {
        "schema_version": "1.0.0",
        "claims": [{"id": "c1", "text": "De conclusie.", "form": {"kind": "atomic", "term": "q"}}],
        "premises": [
            premisse,
            {
                "id": "p2",
                "text": "De brug.",
                "type": premissetype,
                "provenance": {"kind": "user_supplied"},
                "citation": {"source_ref": "Bron", "verification_status": "verified"},
                "thubut": {"label": "certain", "rationale": "handmatig: vastgesteld"},
                "form": {
                    "kind": "conditional",
                    "antecedent": {"kind": "atomic", "term": "p"},
                    "consequent": {"kind": "atomic", "term": "q"},
                },
            },
        ],
        "inferences": [{"id": "i1", "from": ["p1", "p2"], "to": "c1", "scheme": schema}],
    }


def test_het_premissetype_verandert_niets_aan_het_oordeel(motor, sessie):
    """Randvoorwaarde §2.1: één motor, geen aparte rubric per soort premisse.

    Zou er een regel in de rekencode zijn geplant die op het premissetype werkt,
    dan wordt deze test rood. De typen komen uit de lookup-tabel, dus de test
    groeit vanzelf mee als er een type bij komt.
    """
    from sqlalchemy import select

    from bewijsmotor.db.model import LOOKUP_KLASSEN

    typen = sorted(sessie.execute(select(LOOKUP_KLASSEN["premise_type"].key)).scalars())
    assert len(typen) >= 7

    uitkomsten = {}
    for premissetype in typen:
        beoordeling = motor.beoordeel(_stap(premissetype, "deductive"), actor="scherpte")[
            "beoordelingen"
        ][0]
        uitkomsten[premissetype] = (
            beoordeling["probative_force"]["label"],
            beoordeling["weakest_element"]["ref"],
            beoordeling["weakest_element"]["veld"],
            beoordeling["insufficient_evidence"]["waarde"],
            tuple(f["soort"] for f in beoordeling["fallacies"]),
        )

    verschillend = set(uitkomsten.values())
    assert len(verschillend) == 1, f"het premissetype stuurt het oordeel: {uitkomsten}"


def test_het_statuslabel_verandert_niets_aan_het_oordeel(motor):
    """Statusafleiding hoort bij fase 4; fase 1 mag er niet stiekem op reageren."""
    zonder = motor.beoordeel(_stap("revelation_text", "deductive"), actor="scherpte")
    labels = [
        {"label": "muhkam", "opposition": "mutashabih"},
        {"label": "mansukh", "opposition": "nasikh"},
        {"label": "mutashabih", "opposition": "muhkam"},
    ]
    verwacht = zonder["beoordelingen"][0]["probative_force"]["label"]
    for status in labels:
        met = motor.beoordeel(_stap("revelation_text", "deductive", status), actor="scherpte")
        assert met["beoordelingen"][0]["probative_force"]["label"] == verwacht, (
            f"statuslabel {status['label']} stuurt het oordeel"
        )


def test_het_schema_stuurt_de_vragenset_maar_niet_het_label(motor, sessie):
    """Het schema bepaalt welke kritische vragen erbij horen, niet de sterkte.

    De vragen komen uit de geseede vragenset en verschillen per schema; het
    label mag daar niet van afhangen zolang geen vraag faalt.
    """
    from sqlalchemy import select

    from bewijsmotor.db.model import LOOKUP_KLASSEN

    schemas = sorted(sessie.execute(select(LOOKUP_KLASSEN["scheme"].key)).scalars())
    labels = set()
    vragensets = {}
    for schema in schemas:
        beoordeling = motor.beoordeel(_stap("revelation_text", schema), actor="scherpte")[
            "beoordelingen"
        ][0]
        labels.add(beoordeling["probative_force"]["label"])
        vragensets[schema] = len(beoordeling["open_critical_questions"])

    assert len(labels) == 1, f"het schema stuurt de sterkte: {labels}"
    assert len(set(vragensets.values())) > 1, (
        "de vragenset hoort juist wél per schema te verschillen; anders wordt de "
        "geseede vragenset niet gebruikt"
    )
