"""Stap 11: kantelpunten.

Welke ene premisse, stap of kritische vraag zou, indien gewijzigd, het
eindlabel van de claim doen kantelen? De motor kijkt in twee richtingen. Wat het
oordeel omhoog brengt is nuttig ("dit wordt sterk zodra X is aangetoond"), en
wat het breekt evengoed ("dit valt om zodra Y wegvalt").

De analyse draait de hele berekening opnieuw met precies één gewijzigd element.
Er wordt niets benaderd of geïnterpoleerd.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..labels import Schaal
from ..logica.vorm import VormAnalyse
from .berekening import Overschrijving, bereken
from .graaf import Graaf, steunkringen


@dataclass(frozen=True)
class Kantelpunt:
    element_soort: str
    element_ref: str
    veld: str
    huidige_waarde: str
    benodigde_wijziging: str
    kantelt_naar: str
    richting: str
    toelichting: str


def relevante_elementen(graaf: Graaf, claim_ref: str) -> tuple[list[str], list[str]]:
    """De premissen en inferenties waarvan een claim afhangt."""
    premissen: list[str] = []
    inferenties: list[str] = []
    te_doen = [claim_ref]
    gezien_claims: set[str] = set()

    def voeg_premisse_toe(ref: str) -> None:
        if ref in premissen:
            return
        premissen.append(ref)
        premisse = graaf.premisse(ref)
        for sub in premisse.sub_premissen:
            voeg_premisse_toe(sub.ref)
        if premisse.asserts_claim and premisse.asserts_claim not in gezien_claims:
            te_doen.append(premisse.asserts_claim)

    while te_doen:
        huidige = te_doen.pop()
        if huidige in gezien_claims:
            continue
        gezien_claims.add(huidige)
        for inferentie_ref in graaf.lijnen_per_claim.get(huidige, []):
            if inferentie_ref not in inferenties:
                inferenties.append(inferentie_ref)
            for premisse_ref in graaf.inferenties[inferentie_ref].van:
                voeg_premisse_toe(premisse_ref)

    return premissen, inferenties


def zoek(
    graaf: Graaf,
    schaal: Schaal,
    vormanalyses: Mapping[str, VormAnalyse],
    claim_ref: str,
) -> list[Kantelpunt]:
    # De steunkringen zijn een eigenschap van de ontleding en veranderen niet
    # door een hypothetische waarde. Eén keer bepalen volstaat.
    cykels = steunkringen(graaf)
    basis = bereken(graaf, schaal, vormanalyses, cykels=cykels)
    huidig_label = basis.claims[claim_ref].label
    premisse_refs, inferentie_refs = relevante_elementen(graaf, claim_ref)
    gevonden: list[Kantelpunt] = []

    def probeer(overschrijving: Overschrijving) -> str:
        opnieuw = bereken(graaf, schaal, vormanalyses, overschrijving, cykels=cykels)
        return opnieuw.claims[claim_ref].label

    def registreer_labelreeks(
        soort: str,
        ref: str,
        veld: str,
        huidige_waarde: str,
        maak: Callable[[str], Overschrijving],
        toelichting_omhoog: str,
        toelichting_omlaag: str,
    ) -> None:
        for richting, reeks, toelichting in (
            ("upward", schaal.boven(huidige_waarde), toelichting_omhoog),
            ("downward", schaal.onder(huidige_waarde), toelichting_omlaag),
        ):
            for kandidaat in reeks:
                nieuw_label = probeer(maak(kandidaat))
                if nieuw_label != huidig_label:
                    gevonden.append(
                        Kantelpunt(
                            element_soort=soort,
                            element_ref=ref,
                            veld=veld,
                            huidige_waarde=huidige_waarde,
                            benodigde_wijziging=kandidaat,
                            kantelt_naar=nieuw_label,
                            richting=richting,
                            toelichting=toelichting,
                        )
                    )
                    break

    for premisse_ref in premisse_refs:
        uitkomst = basis.premissen[premisse_ref]
        premisse = graaf.premisse(premisse_ref)

        if not uitkomst.heeft_bron:
            met_bron = probeer(Overschrijving(bron={premisse_ref: True}))
            if met_bron != huidig_label:
                gevonden.append(
                    Kantelpunt(
                        element_soort="premise",
                        element_ref=premisse_ref,
                        veld="citation.source_ref",
                        huidige_waarde="geen bron",
                        benodigde_wijziging="een bron aanleveren die deze premisse vaststelt",
                        kantelt_naar=met_bron,
                        richting="upward",
                        toelichting=(
                            "deze premisse noemt geen bron; zodra zij er een heeft, verandert het "
                            "eindlabel"
                            + (
                                " naar wat de reeds aangeleverde score oplevert"
                                if uitkomst.genegeerde_scores
                                else ""
                            )
                        ),
                    )
                )
            continue

        for veld, score in (("thubut", premisse.thubut), ("dalalah", premisse.dalalah)):
            if score is None:
                continue
            registreer_labelreeks(
                "premise",
                premisse_ref,
                veld,
                score.label,
                lambda waarde, r=premisse_ref, v=veld: Overschrijving(**{v: {r: waarde}}),
                f"als de {veld} van deze premisse omhoog gaat, kantelt het eindoordeel",
                f"als de {veld} van deze premisse omlaag gaat, kantelt het eindoordeel",
            )

    for inferentie_ref in inferentie_refs:
        uitkomst = basis.inferenties[inferentie_ref]
        # Bij een bewezen geldige vorm is een ander sterktelabel geen wijziging
        # die iemand kan aanleveren, maar de ontkenning van een vaststelling.
        # De kritische vragen bij die stap blijven wél kantelpunten: een vraag
        # die faalt, zet het label van de stap alsnog op onbepaald.
        if uitkomst.vormstatus != "valid":
            registreer_labelreeks(
                "inference",
                inferentie_ref,
                "strength",
                uitkomst.label,
                lambda waarde, r=inferentie_ref: Overschrijving(inferentie={r: waarde}),
                (
                    "de vorm van deze stap is ongeldig; wordt zij sluitend gemaakt, "
                    "bijvoorbeeld met een van de voorgestelde verzwegen premissen, dan "
                    "kantelt het eindoordeel"
                    if uitkomst.vormstatus == "invalid"
                    else "als deze redeneerstap sterker wordt, kantelt het eindoordeel"
                ),
                "als deze redeneerstap zwakker wordt, kantelt het eindoordeel",
            )

        for vraag in graaf.inferenties[inferentie_ref].kritische_vragen:
            if vraag.beantwoord_door_motor:
                continue
            for kandidaat in ("answered", "unanswered", "failed"):
                if kandidaat == vraag.status:
                    continue
                nieuw_label = probeer(Overschrijving(vraag={vraag.sleutel: kandidaat}))
                if nieuw_label == huidig_label:
                    continue
                richting = (
                    "upward" if schaal.rang(nieuw_label) > schaal.rang(huidig_label) else "downward"
                )
                gevonden.append(
                    Kantelpunt(
                        element_soort="critical_question",
                        element_ref=vraag.sleutel,
                        veld="status",
                        huidige_waarde=vraag.status,
                        benodigde_wijziging=kandidaat,
                        kantelt_naar=nieuw_label,
                        richting=richting,
                        toelichting=f"kritische vraag: {vraag.vraag}",
                    )
                )

    return gevonden
