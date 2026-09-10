"""Stap 12: rapporteren.

Alle assen, de zwakste schakel, de openstaande kritische vragen, de kantelpunten
en de volledige keten, uitklapbaar tot de bron. Nooit één getal.

De rapportage is ook uitklapbaar tot de kernregel: elke bevinding noemt de
kernregel waarop zij steunt, en het rapport draagt de tekst van die kernregels
met hun zelfvernietigingsargument mee. Zo is niet alleen het argument van de
auteur naspeurbaar, maar ook het redeneren van de motor zelf.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..labels import Schaal
from ..logica.vorm import VormAnalyse
from .berekening import Berekening, Bijdrage
from .bevindingen import DrogredenBevinding, VerzwegenVoorstel
from .graaf import Graaf, Premisse
from .kantelpunten import Kantelpunt


def _bijdrage(bijdrage: Bijdrage | None, schaal: Schaal) -> dict[str, Any] | None:
    if bijdrage is None:
        return None
    return {
        "soort": bijdrage.soort,
        "ref": bijdrage.ref,
        "veld": bijdrage.veld,
        "label": bijdrage.label,
        "label_nl": schaal.nl(bijdrage.label),
    }


@dataclass(frozen=True)
class _Ketencontext:
    graaf: Graaf
    berekening: Berekening
    schaal: Schaal
    vormanalyses: Mapping[str, VormAnalyse]
    versie: str


def _premisse_knoop(
    premisse: Premisse, context: _Ketencontext, bezocht: frozenset[str]
) -> dict[str, Any]:
    uitkomst = context.berekening.premissen[premisse.ref]
    schaal = context.schaal
    return {
        "ref": premisse.ref,
        "tekst": premisse.tekst,
        "type": premisse.type,
        "expliciet": premisse.explicit,
        "voorgesteld_door": premisse.proposed_by,
        "bevestigd": premisse.confirmed,
        "herkomst": {
            "kind": premisse.provenance.kind,
            "retrieval_ref": premisse.provenance.retrieval_ref,
            # Ondoorzichtige lading van de indiener reist als tekst mee. Zo blijft
            # zij bewaard zonder dat er een getal in de uitvoer belandt.
            "detail_json": (
                json.dumps(premisse.provenance.detail, ensure_ascii=False, sort_keys=True)
                if premisse.provenance.detail is not None
                else None
            ),
        },
        "citaat": {
            "source_ref": premisse.citation.source_ref,
            "verification_status": premisse.citation.verification_status,
            "toelichting": (
                "de verificatiestatus van een citaat staat los van de sterkte van de claim. "
                "Fase 1 laat haar het label niet beïnvloeden; dat gebeurt vanaf fase 3"
            ),
        },
        "status": (
            {"label": premisse.status.label, "opposition": premisse.status.opposition}
            if premisse.status
            else None
        ),
        "aangeleverde_scores": {
            "thubut": premisse.thubut.als_dict() if premisse.thubut else None,
            "dalalah": premisse.dalalah.als_dict() if premisse.dalalah else None,
        },
        "instrument_output_json": (
            json.dumps(premisse.instrument_output, ensure_ascii=False, sort_keys=True)
            if premisse.instrument_output is not None
            else None
        ),
        "genegeerde_scores": [
            {"veld": veld, "aangeleverd_label": label} for veld, label in uitkomst.genegeerde_scores
        ],
        "berekende_sterkte": {
            "label": uitkomst.label,
            "label_nl": schaal.nl(uitkomst.label),
            "rationale": uitkomst.rationale,
            "computed_by": "engine_kernel",
            "version": context.versie,
        },
        "beweert_claim": premisse.asserts_claim,
        # De keten stopt niet bij de claimgrens. Beweert een premisse een andere
        # claim, dan hangt haar hele onderbouwing eronder, want anders is de
        # keten niet uitklapbaar tot de bron waar zij het zwakst is.
        "keten_van_beweerde_claim": (
            _keten(context, premisse.asserts_claim, bezocht)
            if premisse.asserts_claim and premisse.asserts_claim not in bezocht
            else None
        ),
        "keten_afgekapt_wegens_steunkring": bool(
            premisse.asserts_claim and premisse.asserts_claim in bezocht
        ),
        "sub_premissen": [_premisse_knoop(sub, context, bezocht) for sub in premisse.sub_premissen],
    }


def _keten(context: _Ketencontext, claim_ref: str, bezocht: frozenset[str]) -> dict[str, Any]:
    graaf = context.graaf
    schaal = context.schaal
    claim = graaf.claim(claim_ref)
    claimuitkomst = context.berekening.claims[claim_ref]
    verder = bezocht | {claim_ref}
    lijnen = []
    for inferentie_ref in claimuitkomst.lijnen:
        inferentie = graaf.inferenties[inferentie_ref]
        stap = context.berekening.inferenties[inferentie_ref]
        lijn = context.berekening.lijnen.get(inferentie_ref)
        analyse = context.vormanalyses[inferentie_ref]
        lijnen.append(
            {
                "inferentie_ref": inferentie_ref,
                "is_bepalende_lijn": inferentie_ref == claimuitkomst.bepalende_lijn,
                "schema": inferentie.scheme,
                "interpretatie_ref": inferentie.interpretation_ref,
                "voorgesteld_door": inferentie.proposed_by,
                "bevestigd": inferentie.confirmed,
                "vormtoets": {
                    "status": analyse.status,
                    "toetssoort": analyse.toetssoort,
                    "rationale": analyse.rationale,
                },
                "stapsterkte": {
                    "label": stap.label,
                    "label_nl": schaal.nl(stap.label),
                    "rationale": stap.rationale,
                    "computed_by": "engine_kernel",
                    "version": context.versie,
                    "herkomst": stap.herkomst,
                },
                "lijnsterkte": (
                    {
                        "label": lijn.label,
                        "label_nl": schaal.nl(lijn.label),
                        "rationale": lijn.rationale,
                        "computed_by": "engine_kernel",
                        "version": context.versie,
                        "zwakste": _bijdrage(lijn.zwakste, schaal),
                        "alle_zwakste": [_bijdrage(b, schaal) for b in lijn.alle_zwakste],
                        "raakt_premisse_zonder_bron": lijn.raakt_bronloos,
                    }
                    if lijn
                    else None
                ),
                "kritische_vragen": [
                    {
                        "sleutel": vraag.sleutel,
                        "vraag": vraag.vraag,
                        "status": vraag.status,
                        "effect": vraag.effect,
                        "herkomst": vraag.herkomst,
                        "beantwoord_door_motor": vraag.beantwoord_door_motor,
                        "toelichting": vraag.toelichting,
                    }
                    for vraag in inferentie.kritische_vragen
                ],
                "premissen": [
                    _premisse_knoop(graaf.premisse(ref), context, verder) for ref in inferentie.van
                ],
            }
        )
    return {
        "claim_ref": claim_ref,
        "claim_tekst": claim.tekst,
        "berekende_sterkte": {
            "label": claimuitkomst.label,
            "label_nl": schaal.nl(claimuitkomst.label),
            "rationale": claimuitkomst.rationale,
            "computed_by": "engine_kernel",
            "version": context.versie,
        },
        "bewijslijnen": lijnen,
    }


def keten(
    graaf: Graaf,
    berekening: Berekening,
    schaal: Schaal,
    vormanalyses: Mapping[str, VormAnalyse],
    claim_ref: str,
    versie: str,
) -> dict[str, Any]:
    """De volledige keten van één claim, uitklapbaar tot de bron."""
    context = _Ketencontext(
        graaf=graaf,
        berekening=berekening,
        schaal=schaal,
        vormanalyses=vormanalyses,
        versie=versie,
    )
    return _keten(context, claim_ref, frozenset())


def bouw_beoordeling(
    graaf: Graaf,
    berekening: Berekening,
    schaal: Schaal,
    vormanalyses: Mapping[str, VormAnalyse],
    claim_ref: str,
    drogredenen: Sequence[DrogredenBevinding],
    verzwegen: Sequence[VerzwegenVoorstel],
    kantelpunten: Sequence[Kantelpunt],
    kernregels: Mapping[str, Mapping[str, str]],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    claimuitkomst = berekening.claims[claim_ref]
    eigen_inferenties = _bereikbare_inferenties(graaf, claim_ref)
    bereikbare_claims = _bereikbare_claims(graaf, claim_ref)

    open_vragen = [
        {
            "inferentie_ref": ref,
            "sleutel": vraag.sleutel,
            "vraag": vraag.vraag,
            "status": vraag.status,
            "effect": vraag.effect,
            "herkomst": vraag.herkomst,
        }
        for ref in sorted(eigen_inferenties)
        for vraag in graaf.inferenties[ref].kritische_vragen
        if vraag.status != "answered"
    ]
    # Een lege lijst openstaande vragen kan twee dingen betekenen: er waren er
    # geen, of de indiener heeft ze zelf afgevinkt. Dat verschil hoort zichtbaar
    # te zijn, want een antwoord van de indiener is een bewering, geen toets.
    beantwoorde_vragen = [
        {
            "inferentie_ref": ref,
            "sleutel": vraag.sleutel,
            "vraag": vraag.vraag,
            "beantwoord_door": (
                "motor" if vraag.beantwoord_door_motor else "de indiener van de tekst"
            ),
            "toelichting": vraag.toelichting,
        }
        for ref in sorted(eigen_inferenties)
        for vraag in graaf.inferenties[ref].kritische_vragen
        if vraag.status == "answered"
    ]

    eigen_drogredenen = [
        d
        for d in drogredenen
        if (d.element_soort == "inference" and d.element_ref in eigen_inferenties)
        or (d.element_soort == "claim" and d.element_ref == claim_ref)
    ]
    eigen_verzwegen = [v for v in verzwegen if v.inferentie_ref in eigen_inferenties]

    # De zwakste-schakelregel en de steunregel worden bij elke berekening
    # toegepast. De overige komen uit de bevindingen zelf, en welke kernregel
    # een soort bevinding draagt staat in de lookup-tabel, niet in deze code.
    gebruikte_kernregels = {"zwakste_schakel", "steun_en_bewijslast"}
    gebruikte_kernregels.update(d.kernregel for d in eigen_drogredenen)
    gebruikte_kernregels.update(v.kernregel for v in eigen_verzwegen)
    if any(
        vormanalyses[ref].status != "not_testable"
        for ref in eigen_inferenties
        if ref in vormanalyses
    ):
        gebruikte_kernregels.add("vorm_versus_waarheid")

    return {
        "claim_ref": claim_ref,
        "claim_tekst": graaf.claim(claim_ref).tekst,
        "profiel": {
            "naam": metadata["profiel_naam"],
            "versie": metadata["profiel_versie"],
            "qawaid_geladen": metadata["qawaid_geladen"],
            "burden_allocation": metadata["burden_allocation"],
        },
        "competentieniveau": graaf.competentieniveau,
        "gebruiksvorm": graaf.gebruiksvorm,
        "versies": metadata["versies"],
        "probative_force": {
            "label": claimuitkomst.label,
            "label_nl": schaal.nl(claimuitkomst.label),
            "rationale": claimuitkomst.rationale,
            "computed_by": "engine_kernel",
            "version": metadata["versies"]["motor"],
        },
        "dialectical_force": {
            "berekend": False,
            "tegen_profielen": [],
            "toelichting": (
                "dialectische kracht wordt op aanvraag tegen een opgegeven profiel berekend, "
                "niet vooraf tegen alle profielen. Fase 1 kent geen profielen met regels en "
                "berekent haar daarom niet"
            ),
        },
        "falsifiability_exposure": {
            "beoordeeld": False,
            "toelichting": (
                "hoeveel de claim uitsluit, is een aparte as naast sterkte. Fase 1 berekent haar "
                "niet; zij wordt niet stilzwijgend als sterkte meegeteld"
            ),
        },
        "weakest_element": _bijdrage(claimuitkomst.zwakste, schaal),
        "alle_zwakste_elementen": [_bijdrage(b, schaal) for b in claimuitkomst.alle_zwakste],
        "open_critical_questions": open_vragen,
        "answered_critical_questions": beantwoorde_vragen,
        "fallacy_scan": metadata["drogredenscan"],
        "fallacies": [
            {
                "soort": d.soort,
                "element_soort": d.element_soort,
                "element_ref": d.element_ref,
                "rationale": d.rationale,
                "kernregel": d.kernregel,
            }
            for d in eigen_drogredenen
        ],
        "possible_unstated_premises": [
            {
                "inferentie_ref": v.inferentie_ref,
                "voorstel": v.voorstel,
                "vorm": v.vorm,
                "basis": v.basis,
                "kernregel": v.kernregel,
                "rationale": v.rationale,
                "voorgesteld_door": v.proposed_by,
                "bevestigd": v.confirmed,
                "telt_mee_in_de_sterkte": False,
            }
            for v in eigen_verzwegen
        ],
        "tipping_points": [
            {
                "element_soort": k.element_soort,
                "element_ref": k.element_ref,
                "veld": k.veld,
                "current_label": k.huidige_waarde,
                "change_needed": k.benodigde_wijziging,
                "would_flip_to": k.kantelt_naar,
                "richting": k.richting,
                "toelichting": k.toelichting,
            }
            for k in kantelpunten
        ],
        "insufficient_evidence": {
            "waarde": claimuitkomst.onvoldoende_bewijs,
            "uitleg": claimuitkomst.onvoldoende_uitleg,
            "premissen_zonder_bron": [
                ref
                for ref in berekening.bronloze_premissen
                if ref in _bereikbare_premissen(graaf, claim_ref)
            ],
        },
        "steunkring": {
            "gevonden": bool(claimuitkomst.in_cykel),
            # De kring waarin deze claim zelf ligt, en de kringen die verderop in
            # haar eigen keten liggen. Kringen elders in de inzending horen in het
            # rapport van die andere claim, niet in dit rapport.
            "kringen_van_deze_claim": [
                list(kring) for kring in berekening.cykels if claim_ref in kring
            ],
            "kringen_in_de_keten": [
                list(kring)
                for kring in berekening.cykels
                if claim_ref not in kring and set(kring) & bereikbare_claims
            ],
        },
        "chain": keten(
            graaf, berekening, schaal, vormanalyses, claim_ref, metadata["versies"]["motor"]
        ),
        "kernel_rules_applied": [
            {
                "key": sleutel,
                "statement": kernregels[sleutel]["statement_nl"],
                "self_refutation_argument": kernregels[sleutel]["self_refutation_argument"],
            }
            for sleutel in sorted(gebruikte_kernregels)
            if sleutel in kernregels
        ],
        "voorbehouden": metadata["voorbehouden"],
        "interim_regels": metadata["interim_regels"],
    }


def _bereikbare_claims(graaf: Graaf, claim_ref: str) -> set[str]:
    """Alle claims waarop deze claim langs haar keten steunt, zichzelf inbegrepen."""
    gevonden: set[str] = set()
    te_doen = [claim_ref]
    while te_doen:
        huidige = te_doen.pop()
        if huidige in gevonden:
            continue
        gevonden.add(huidige)
        for inferentie_ref in graaf.lijnen_per_claim.get(huidige, []):
            for premisse_ref in graaf.inferenties[inferentie_ref].van:
                te_doen.extend(_beweerde(graaf, premisse_ref))
    return gevonden


def _bereikbare_inferenties(graaf: Graaf, claim_ref: str) -> set[str]:
    gevonden: set[str] = set()
    te_doen = [claim_ref]
    gezien: set[str] = set()
    while te_doen:
        huidige = te_doen.pop()
        if huidige in gezien:
            continue
        gezien.add(huidige)
        for inferentie_ref in graaf.lijnen_per_claim.get(huidige, []):
            gevonden.add(inferentie_ref)
            for premisse_ref in graaf.inferenties[inferentie_ref].van:
                te_doen.extend(_beweerde(graaf, premisse_ref))
    return gevonden


def _bereikbare_premissen(graaf: Graaf, claim_ref: str) -> set[str]:
    gevonden: set[str] = set()
    for inferentie_ref in _bereikbare_inferenties(graaf, claim_ref):
        for premisse_ref in graaf.inferenties[inferentie_ref].van:
            _verzamel_premisse(graaf, premisse_ref, gevonden)
    return gevonden


def _verzamel_premisse(graaf: Graaf, ref: str, gevonden: set[str]) -> None:
    if ref in gevonden:
        return
    gevonden.add(ref)
    for sub in graaf.premisse(ref).sub_premissen:
        _verzamel_premisse(graaf, sub.ref, gevonden)


def _beweerde(graaf: Graaf, premisse_ref: str) -> list[str]:
    premisse = graaf.premisse(premisse_ref)
    gevonden: list[str] = []
    if premisse.asserts_claim:
        gevonden.append(premisse.asserts_claim)
    for sub in premisse.sub_premissen:
        gevonden.extend(_beweerde(graaf, sub.ref))
    return gevonden
