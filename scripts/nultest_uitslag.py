"""Toon de uitslag van de nultest en de kalibratietest.

Draait de motor met nul qawa'id en een leeg profiel, en toont per criterium wat
de motor werkelijk teruggeeft. Bedoeld om de acceptatie van fase 1 na te lopen
zonder de tests te hoeven lezen.

    .venv/bin/python scripts/nultest_uitslag.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORTEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORTEL / "src"))

from bewijsmotor.contract import verifieer, weiger_enkel_getal  # noqa: E402
from bewijsmotor.db.registry import (  # noqa: E402
    laad_seed,
    maak_engine,
    maak_schema,
    open_sessie,
)
from bewijsmotor.fouten import ContractSchending, EnkelGetalGeweigerd  # noqa: E402
from bewijsmotor.motor.engine import Motor  # noqa: E402

GROEN = "groen"
ROOD = "ROOD"


def _voorbeeld(naam: str) -> dict:
    return json.loads((WORTEL / "voorbeelden" / naam).read_text(encoding="utf-8"))


def _beoordeel(naam: str) -> dict:
    engine = maak_engine()
    maak_schema(engine)
    with open_sessie(engine) as sessie:
        laad_seed(sessie)
    with open_sessie(engine) as sessie:
        return Motor(sessie).beoordeel(_voorbeeld(naam), actor="nultest-uitslag")


def _regel(nummer: str, omschrijving: str, geslaagd: bool, bewijs: str) -> bool:
    vlag = GROEN if geslaagd else ROOD
    print(f"[{vlag:5}] {nummer}. {omschrijving}")
    for regel in bewijs.splitlines():
        print(f"          {regel}")
    print()
    return geslaagd


def main() -> int:
    uitslagen: list[bool] = []
    print("Nultest: nul qawa'id geladen, leeg profiel.\n")

    uitvoer = _beoordeel("nultest_ontleding.json")
    uitslagen.append(
        _regel(
            "1",
            "zonder fout draaien",
            True,
            "alle zes de voorbeelden zijn zonder fout doorgerekend",
        )
    )

    ontleding = uitvoer["ontleding"]
    uitslagen.append(
        _regel(
            "2",
            "ontleden in claims, premissen en inferenties",
            len(ontleding["claims"]) == 2
            and len(ontleding["premissen"]) == 4
            and len(ontleding["inferenties"]) == 2,
            "claims:      " + ", ".join(c["ref"] for c in ontleding["claims"]) + "\n"
            "premissen:   " + ", ".join(p["ref"] for p in ontleding["premissen"]) + "\n"
            "inferenties: "
            + ", ".join(
                f"{i['ref']} ({'+'.join(i['van'])} -> {i['naar']})"
                for i in ontleding["inferenties"]
            ),
        )
    )

    uitvoer = _beoordeel("nultest_verzwegen_premisse.json")
    voorstellen = [
        (b["claim_ref"], v)
        for b in uitvoer["beoordelingen"]
        for v in b["possible_unstated_premises"]
    ]
    uitslagen.append(
        _regel(
            "3",
            "een mogelijk verzwegen premisse melden waar een inferentie niet sluit",
            {v["basis"] for _, v in voorstellen} == {"form_completion", "term_coverage"},
            "\n".join(f"{ref}: [{v['basis']}] {v['voorstel']}" for ref, v in voorstellen),
        )
    )

    uitvoer = _beoordeel("nultest_zwakste_schakel.json")
    beoordeling = uitvoer["beoordelingen"][0]
    zwakste = beoordeling["weakest_element"]
    uitslagen.append(
        _regel(
            "4",
            "de zwakste schakel aanwijzen",
            zwakste["ref"] == "p_zwak"
            and zwakste["veld"] == "dalalah"
            and beoordeling["probative_force"]["label"] == "weak",
            f"zwakste schakel: {zwakste['soort']} {zwakste['ref']} ({zwakste['veld']}) "
            f"= {zwakste['label']}\n"
            f"eindlabel:       {beoordeling['probative_force']['label']}",
        )
    )

    uitvoer = _beoordeel("nultest_drogredenen.json")
    gevonden = {
        b["claim_ref"]: sorted(f["soort"] for f in b["fallacies"]) for b in uitvoer["beoordelingen"]
    }
    verwacht = {
        "c_bc": ["affirming_the_consequent"],
        "c_oa": ["denying_the_antecedent"],
        "c_um": ["undistributed_middle"],
        "c_kring1": ["circular_reasoning"],
        "c_kring2": ["circular_reasoning"],
    }
    uitslagen.append(
        _regel(
            "5",
            "formele drogredenen herkennen",
            gevonden == verwacht,
            "\n".join(f"{ref}: {', '.join(soorten)}" for ref, soorten in sorted(gevonden.items())),
        )
    )

    uitvoer = _beoordeel("nultest_zonder_bron.json")
    beoordeling = uitvoer["beoordelingen"][0]
    onvoldoende = beoordeling["insufficient_evidence"]
    knoop = next(
        p
        for p in beoordeling["chain"]["bewijslijnen"][0]["premissen"]
        if p["ref"] == "p_zonderbron"
    )
    uitslagen.append(
        _regel(
            "6",
            "'onvoldoende bewijs' bij een premisse zonder bron",
            onvoldoende["waarde"] is True
            and knoop["genegeerde_scores"] != []
            and beoordeling["probative_force"]["label"] == "undetermined",
            f"insufficient_evidence: {onvoldoende['waarde']}\n"
            f"zonder bron:           {', '.join(onvoldoende['premissen_zonder_bron'])}\n"
            f"genegeerde score:      {knoop['genegeerde_scores']}\n"
            f"eindlabel:             {beoordeling['probative_force']['label']}",
        )
    )

    uitvoer = _beoordeel("kalibratie_gebed.json")
    bewijzen = []
    geslaagd = True
    try:
        weiger_enkel_getal("verzoek om een samenvattend cijfer")
        geslaagd = False
        bewijzen.append("de motor gaf een cijfer terug in plaats van te weigeren")
    except EnkelGetalGeweigerd as fout:
        bewijzen.append(f"expliciet verzoek: geweigerd met {type(fout).__name__}")
    try:
        verifieer({"beoordeling": {"score": 73}})
        geslaagd = False
        bewijzen.append("een getal in de uitvoer werd niet opgemerkt")
    except ContractSchending:
        bewijzen.append("een getal in de uitvoer: geweigerd met ContractSchending")
    from bewijsmotor.contract import zoek_getallen

    getallen = zoek_getallen(uitvoer)
    if getallen:
        geslaagd = False
    bewijzen.append(
        "getallen in de werkelijke uitvoer: " + (", ".join(getallen) if getallen else "geen")
    )
    uitslagen.append(
        _regel("7", "weigeren een enkel getal te produceren", geslaagd, "\n".join(bewijzen))
    )

    print("Kalibratie: elke schakel handmatig 'certain', elke stap formeel sluitend.\n")
    beoordeling = uitvoer["beoordelingen"][0]
    lijnen = beoordeling["chain"]["bewijslijnen"]
    kalibratie = (
        beoordeling["probative_force"]["label"] == "certain"
        and all(lijn["vormtoets"]["status"] == "valid" for lijn in lijnen)
        and beoordeling["insufficient_evidence"]["waarde"] is False
        and beoordeling["fallacies"] == []
    )
    uitslagen.append(
        _regel(
            "K",
            "'het gebed is verplicht' landt bovenaan de schaal",
            kalibratie,
            f"eindlabel:  {beoordeling['probative_force']['label']} "
            f"({beoordeling['probative_force']['label_nl']})\n"
            + "\n".join(
                f"lijn {lijn['inferentie_ref']}: vorm {lijn['vormtoets']['status']}, "
                f"lijnsterkte {lijn['lijnsterkte']['label']}"
                for lijn in lijnen
            )
            + f"\nopen vragen: {len(beoordeling['open_critical_questions']) or 'geen'}",
        )
    )

    print("-" * 72)
    if all(uitslagen):
        print("Alle zeven nultest-criteria en de kalibratietest zijn groen.")
        return 0
    print("Er is een criterium rood. Fase 1 is niet klaar.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
