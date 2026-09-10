"""Verwijderplicht voor de interim-regels van §4.5.

Elke interim-regel krijgt hier een test die **faalt** zodra het vervangende
mechanisme bestaat en de regel er nog is. Een interim-regel die stil blijft
staan is de meest voorspelbare fout in een gefaseerd bouwplan, en dit is de
enige bewaking die niet afhangt van iemands geheugen.

De bewaking is tweezijdig, want ook het omgekeerde is fout. §4.5 zegt dat deze
regels in fase 1 **gelden**; wie ze weghaalt voordat de vervanger er is, breekt
het gedrag dat de spec voorschrijft. Elke test toetst daarom één invariant:

    de interim-regel is in werking dan en slechts dan als haar vervanger ontbreekt

Twee dingen worden apart vastgesteld.

*Bestaat de vervanger?* Dat wordt afgelezen aan sporen die het bouwen van dat
mechanisme onvermijdelijk achterlaat: een modulenaam, een gedefinieerde functie
of klasse, of een afhankelijkheid. Er wordt niet in commentaar of documentatie
gezocht en niet op een vlag vertrouwd die iemand moet omzetten; een vlag die je
vergeet om te zetten is precies de fout die deze test moet vangen.

*Werkt de interim-regel nog?* Dat wordt afgelezen aan het gedrag van de motor,
niet aan de tekst van de code. Een regel die is uitgeschakeld maar wel nog in
commentaar staat, telt als weg.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from bewijsmotor.interim import REGELS_OP_SLEUTEL

WORTEL = Path(__file__).resolve().parents[1]
BRON = WORTEL / "src" / "bewijsmotor"


@dataclass(frozen=True)
class Sporen:
    """Waaraan te zien is dat het vervangende mechanisme is gebouwd."""

    modulenamen: tuple[str, ...] = ()
    definities: tuple[str, ...] = ()
    afhankelijkheden: tuple[str, ...] = ()
    uitvoersleutels: tuple[str, ...] = field(default=())


SPOREN: dict[str, Sporen] = {
    # B3: de nederlaaggraaf met grounded semantics. De spec schrijft voor een
    # bestaande bibliotheek te gebruiken, dus die verschijnt in de afhankelijkheden.
    "gefaalde_kritische_vraag": Sporen(
        modulenamen=("nederlaaggraaf", "defeat", "grounded", "aanvalsemantiek", "aanvalgraaf"),
        definities=(
            "grounded_semantics",
            "nederlaaggraaf",
            "defeat_graph",
            "bouw_nederlaaggraaf",
            "bereken_nederlaag",
            "aanvalsemantiek",
        ),
        afhankelijkheden=("dung", "argumentation", "pyarg", "aspartix", "clingo", "pyglaf"),
        uitvoersleutels=("nederlaaggraaf", "defeat_status", "verslagen"),
    ),
    # De vervanger is noisy-OR met de afbeelding van labels op kansen als qaida.
    "convergente_steun": Sporen(
        modulenamen=("noisy", "convergentie", "convergence"),
        definities=(
            "noisy_or",
            "convergentiebonus",
            "verhoog_bij_convergentie",
            "label_naar_kans",
            "kansafbeelding",
        ),
        uitvoersleutels=("convergentiebonus", "noisy_or"),
    ),
    # Fase 5: de taalmodelstap die verzwegen premissen voorstelt.
    "verzwegen_premissen": Sporen(
        modulenamen=("llm", "taalmodel"),
        definities=("llm_voorstel", "vraag_taalmodel", "stel_structuur_voor", "llm_ontleding"),
        afhankelijkheden=("anthropic", "openai", "litellm", "langchain", "transformers"),
    ),
}


def _gedefinieerde_namen() -> set[str]:
    """Elke functie- en klassenaam in de motor. Commentaar telt niet mee."""
    namen: set[str] = set()
    for pad in BRON.rglob("*.py"):
        tekst = pad.read_text(encoding="utf-8")
        namen.update(re.findall(r"^\s*(?:async\s+)?def\s+(\w+)", tekst, flags=re.MULTILINE))
        namen.update(re.findall(r"^\s*class\s+(\w+)", tekst, flags=re.MULTILINE))
    return namen


def _modulestammen() -> set[str]:
    return {pad.stem for pad in BRON.rglob("*.py")}


def _afhankelijkheden() -> str:
    tekst = (WORTEL / "pyproject.toml").read_text(encoding="utf-8")
    lockfile = WORTEL / "requirements.lock"
    if lockfile.exists():
        tekst += "\n" + lockfile.read_text(encoding="utf-8")
    return tekst.lower()


def _gevonden_sporen(sleutel: str, uitvoer: dict | None = None) -> list[str]:
    sporen = SPOREN[sleutel]
    gevonden: list[str] = []

    stammen = _modulestammen()
    for marker in sporen.modulenamen:
        for stam in stammen:
            if marker in stam.lower():
                gevonden.append(f"module '{stam}.py' bevat '{marker}'")

    namen = _gedefinieerde_namen()
    for marker in sporen.definities:
        for naam in namen:
            if marker in naam.lower():
                gevonden.append(f"gedefinieerde naam '{naam}' bevat '{marker}'")

    if sporen.afhankelijkheden:
        pakketten = _afhankelijkheden()
        for marker in sporen.afhankelijkheden:
            if re.search(rf"^\s*[\"']?{re.escape(marker)}[\w\-]*\s*[=<>~\"']", pakketten, re.M):
                gevonden.append(f"afhankelijkheid met '{marker}' is gedeclareerd")

    if uitvoer is not None:
        for marker in sporen.uitvoersleutels:
            if marker in str(uitvoer.keys()).lower():
                gevonden.append(f"de beoordeling draagt een as met '{marker}'")

    return sorted(set(gevonden))


# --------------------------------------------------------------------------
# Invoer voor de gedragsproeven
# --------------------------------------------------------------------------


def _premisse(ref: str, label: str, vorm: dict) -> dict:
    return {
        "id": ref,
        "text": f"Premisse {ref}.",
        "type": "sense_observation",
        "provenance": {"kind": "user_supplied"},
        "citation": {"source_ref": f"Bron {ref}", "verification_status": "verified"},
        "thubut": {"label": label, "rationale": "handmatig ingevoerd voor deze proef"},
        "form": vorm,
    }


def _keten(gefaalde_vraag: bool) -> dict:
    vragen = (
        [
            {
                "question": "Klopt de aanname achter deze stap?",
                "status": "failed",
                "effect": "undercut",
            }
        ]
        if gefaalde_vraag
        else []
    )
    return {
        "schema_version": "1.0.0",
        "claims": [{"id": "c1", "text": "De conclusie.", "form": {"kind": "atomic", "term": "q"}}],
        "premises": [
            _premisse("p1", "certain", {"kind": "atomic", "term": "p"}),
            _premisse(
                "p2",
                "certain",
                {
                    "kind": "conditional",
                    "antecedent": {"kind": "atomic", "term": "p"},
                    "consequent": {"kind": "atomic", "term": "q"},
                },
            ),
        ],
        "inferences": [
            {
                "id": "i1",
                "from": ["p1", "p2"],
                "to": "c1",
                "scheme": "deductive",
                "critical_questions": vragen,
            }
        ],
    }


def _twee_onafhankelijke_lijnen() -> dict:
    return {
        "schema_version": "1.0.0",
        "claims": [{"id": "c1", "text": "De conclusie.", "form": {"kind": "atomic", "term": "q"}}],
        "premises": [
            _premisse("p1", "probable", {"kind": "atomic", "term": "p"}),
            _premisse(
                "p2",
                "probable",
                {
                    "kind": "conditional",
                    "antecedent": {"kind": "atomic", "term": "p"},
                    "consequent": {"kind": "atomic", "term": "q"},
                },
            ),
            _premisse("p3", "probable", {"kind": "atomic", "term": "r"}),
            _premisse(
                "p4",
                "probable",
                {
                    "kind": "conditional",
                    "antecedent": {"kind": "atomic", "term": "r"},
                    "consequent": {"kind": "atomic", "term": "q"},
                },
            ),
        ],
        "inferences": [
            {"id": "i1", "from": ["p1", "p2"], "to": "c1", "scheme": "deductive"},
            {"id": "i2", "from": ["p3", "p4"], "to": "c1", "scheme": "deductive"},
        ],
    }


def _stap_zonder_vorm() -> dict:
    return {
        "schema_version": "1.0.0",
        "claims": [
            {
                "id": "c1",
                "text": "De conclusie.",
                "terms": ["grond", "term_die_in_geen_premisse_staat"],
            }
        ],
        "premises": [
            {
                "id": "p1",
                "text": "De grond.",
                "type": "sense_observation",
                "provenance": {"kind": "user_supplied"},
                "citation": {"source_ref": "Bron", "verification_status": "verified"},
                "thubut": {"label": "strong", "rationale": "handmatig ingevoerd voor deze proef"},
                "terms": ["grond"],
            }
        ],
        "inferences": [{"id": "i1", "from": ["p1"], "to": "c1", "scheme": "deductive"}],
    }


# --------------------------------------------------------------------------
# De drie bewakingen
# --------------------------------------------------------------------------


def _meld(sleutel: str, sporen: list[str], regel_actief: bool) -> str:
    regel = REGELS_OP_SLEUTEL[sleutel]
    if sporen and regel_actief:
        return (
            f"Interim-regel '{regel.naam}' ({regel.spec}) staat er nog, terwijl haar vervanger "
            f"bestaat: {regel.vervangen_door}.\n"
            "Aangetroffen sporen van dat mechanisme:\n  "
            + "\n  ".join(sporen)
            + f"\nHaal de interim-regel weg uit {', '.join(regel.toegepast_in)}, schrap haar uit "
            "bewijsmotor/interim.py, en verwijder deze bewaking."
        )
    return (
        f"Interim-regel '{regel.naam}' ({regel.spec}) is niet meer in werking, terwijl haar "
        f"vervanger nog niet bestaat: {regel.vervangen_door}.\n"
        f"§4.5 zegt dat deze regel in fase 1 geldt en vervalt in {regel.vervalt_in}. "
        "Zet haar terug, of bouw eerst de vervanger."
    )


def test_verwijderplicht_gefaalde_kritische_vraag(motor):
    """De regel plafonneert op onbepaald; vervalt zodra de nederlaaggraaf bestaat."""
    schoon = motor.beoordeel(_keten(gefaalde_vraag=False), actor="verwijderplicht")
    gebroken = motor.beoordeel(_keten(gefaalde_vraag=True), actor="verwijderplicht")

    assert schoon["beoordelingen"][0]["probative_force"]["label"] == "certain", (
        "de proef deugt niet: zonder gefaalde vraag hoort deze keten zeker te zijn"
    )
    regel_actief = gebroken["beoordelingen"][0]["probative_force"]["label"] == "undetermined"
    sporen = _gevonden_sporen("gefaalde_kritische_vraag", gebroken["beoordelingen"][0])

    assert regel_actief == (not sporen), _meld("gefaalde_kritische_vraag", sporen, regel_actief)


def test_verwijderplicht_convergente_steun(motor):
    """Maximum over lijnen zonder bonus; vervalt zodra noisy-OR bestaat."""
    uitvoer = motor.beoordeel(_twee_onafhankelijke_lijnen(), actor="verwijderplicht")
    beoordeling = uitvoer["beoordelingen"][0]
    lijnen = beoordeling["chain"]["bewijslijnen"]

    assert len(lijnen) == 2, "de proef deugt niet: er horen twee onafhankelijke lijnen te zijn"
    assert {lijn["lijnsterkte"]["label"] for lijn in lijnen} == {"probable"}, (
        "de proef deugt niet: beide lijnen horen op 'waarschijnlijk' uit te komen"
    )

    # Zonder bonus is de claim het maximum over de lijnen, dus precies 'probable'.
    # Met noisy-OR zou twee keer 'waarschijnlijk' samen hoger uitkomen.
    regel_actief = beoordeling["probative_force"]["label"] == "probable"
    sporen = _gevonden_sporen("convergente_steun", beoordeling)

    assert regel_actief == (not sporen), _meld("convergente_steun", sporen, regel_actief)


def test_verwijderplicht_verzwegen_premissen(motor):
    """De termdekkingsheuristiek; vervalt of wordt aangevuld zodra de LLM-stap bestaat.

    §4.5 laat bij deze regel twee uitkomsten toe: vervallen of aangevuld worden.
    Deze bewaking dwingt daarom geen verwijdering af maar een besluit: zodra de
    taalmodelstap bestaat, moet iemand kiezen en deze test bijwerken. Stil laten
    staan is de fout die §4.5 wil voorkomen.
    """
    uitvoer = motor.beoordeel(_stap_zonder_vorm(), actor="verwijderplicht")
    voorstellen = uitvoer["beoordelingen"][0]["possible_unstated_premises"]
    via_termdekking = [v for v in voorstellen if v["basis"] == "term_coverage"]

    regel_actief = bool(via_termdekking) and all(
        v["voorstel"].startswith("mogelijk verzwegen premisse") and "heuristiek" in v["rationale"]
        for v in via_termdekking
    )
    sporen = _gevonden_sporen("verzwegen_premissen", uitvoer["beoordelingen"][0])

    if sporen and regel_actief:
        pytest.fail(
            _meld("verzwegen_premissen", sporen, regel_actief)
            + "\nLet op: §4.5 laat hier twee uitkomsten toe, vervallen of aangevuld worden. "
            "Leg de keuze vast en werk deze bewaking bij; het besluit mag niet uitblijven."
        )
    assert regel_actief, _meld("verzwegen_premissen", sporen, regel_actief)


def test_elke_interim_regel_heeft_een_bewaking():
    """Een nieuwe interim-regel zonder bewaking is precies het gat dat §4.5 dicht."""
    bewaakt = set(SPOREN)
    beschreven = set(REGELS_OP_SLEUTEL)
    assert bewaakt == beschreven, (
        f"zonder bewaking: {sorted(beschreven - bewaakt)}; "
        f"bewaking zonder regel: {sorted(bewaakt - beschreven)}"
    )
    for sleutel, regel in REGELS_OP_SLEUTEL.items():
        assert regel.vervangen_door, f"{sleutel} zegt niet wat haar vervangt"
        assert regel.vervalt_in, f"{sleutel} zegt niet wanneer zij vervalt"
        assert SPOREN[sleutel].modulenamen or SPOREN[sleutel].definities, (
            f"{sleutel} heeft geen enkel spoor om de vervanger aan te herkennen"
        )


def test_de_bewaking_kijkt_niet_naar_commentaar():
    """Prose mag de bewaking niet laten afgaan, anders is zij onbruikbaar.

    De woorden 'nederlaaggraaf' en 'noisy-OR' staan nu in commentaar en in
    rationales, precies omdat de code uitlegt wat haar later vervangt. Zou de
    bewaking daarop afgaan, dan stond zij vanaf dag één op rood.
    """
    tekst = "\n".join(pad.read_text(encoding="utf-8") for pad in BRON.rglob("*.py"))
    assert "nederlaaggraaf" in tekst, "de proef deugt niet: het woord hoort in commentaar te staan"
    assert _gevonden_sporen("gefaalde_kritische_vraag") == []
    assert _gevonden_sporen("convergente_steun") == []
    assert _gevonden_sporen("verzwegen_premissen") == []
