"""Stap 10: zekerheid. De zwakste-schakelregel, toegepast op de hele keten.

Deze module is één zuivere functie met hulpstructuren. Zij leest geen database
en schrijft niets weg, zodat stap 11 haar met één gewijzigd element opnieuw kan
draaien om kantelpunten te vinden.

Twee rekenregels, beide met hun reden in de uitvoer:

* **Binnen één bewijslijn geldt het minimum.** Een conclusie kan niet zekerder
  zijn dan haar zwakste premisse of haar zwakste stap (kernregel
  ``zwakste_schakel``).
* **Over bewijslijnen heen geldt het maximum.** Een claim met één sluitende
  bewijslijn en daarnaast een slechte lijn is door die slechte lijn niet
  zwakker geworden. Fase 1 kent geen verhoging door convergentie; die vraagt
  een afbeelding van labels op kansen, en dat is een instelbare regel, geen
  kernregel.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ..labels import Schaal
from ..logica.vorm import VormAnalyse
from .graaf import Graaf, claim_afhankelijkheden, topologische_volgorde, zoek_cykels


@dataclass(frozen=True)
class Overschrijving:
    """Eén hypothetische wijziging, voor de kantelpuntanalyse."""

    thubut: Mapping[str, str] = field(default_factory=dict)
    dalalah: Mapping[str, str] = field(default_factory=dict)
    inferentie: Mapping[str, str] = field(default_factory=dict)
    vraag: Mapping[str, str] = field(default_factory=dict)
    # Premissen die hypothetisch wél een bron hebben. Zo is te tonen wat het
    # aanleveren van een bron met het oordeel zou doen.
    bron: Mapping[str, bool] = field(default_factory=dict)


LEEG = Overschrijving()


@dataclass
class Bijdrage:
    soort: str  # premise | claim | inference | score
    ref: str
    veld: str | None
    label: str


@dataclass
class PremisseUitkomst:
    ref: str
    label: str
    rationale: str
    bijdragen: list[Bijdrage]
    heeft_bron: bool
    raakt_bronloos: bool
    genegeerde_scores: list[tuple[str, str]]


@dataclass
class InferentieUitkomst:
    ref: str
    label: str
    rationale: str
    vormstatus: str
    herkomst: str  # formeel | aangeleverd | onbepaald | overschrijving
    gefaalde_vragen: list[str]


@dataclass
class LijnUitkomst:
    inferentie_ref: str
    claim_ref: str
    label: str
    zwakste: Bijdrage | None
    alle_zwakste: list[Bijdrage]
    raakt_bronloos: bool


@dataclass
class ClaimUitkomst:
    ref: str
    label: str
    rationale: str
    bepalende_lijn: str | None
    lijnen: list[str]
    onvoldoende_bewijs: bool
    onvoldoende_uitleg: str
    in_cykel: bool
    zwakste: Bijdrage | None
    alle_zwakste: list[Bijdrage]


@dataclass
class Berekening:
    premissen: dict[str, PremisseUitkomst]
    inferenties: dict[str, InferentieUitkomst]
    lijnen: dict[str, LijnUitkomst]
    claims: dict[str, ClaimUitkomst]
    cykels: list[tuple[str, ...]]
    bronloze_premissen: list[str]


def bereken(
    graaf: Graaf,
    schaal: Schaal,
    vormanalyses: Mapping[str, VormAnalyse],
    overschrijving: Overschrijving = LEEG,
    cykels: list[tuple[str, ...]] | None = None,
) -> Berekening:
    afhankelijk = claim_afhankelijkheden(graaf)
    if cykels is None:
        cykels = zoek_cykels(afhankelijk)
    in_cykel: set[str] = {knoop for cykel in cykels for knoop in cykel}
    volgorde = topologische_volgorde(afhankelijk, in_cykel)

    premisse_uitkomsten: dict[str, PremisseUitkomst] = {}
    inferentie_uitkomsten: dict[str, InferentieUitkomst] = {}
    lijn_uitkomsten: dict[str, LijnUitkomst] = {}
    claim_uitkomsten: dict[str, ClaimUitkomst] = {}

    def premisse_uitkomst(ref: str) -> PremisseUitkomst:
        if ref in premisse_uitkomsten:
            return premisse_uitkomsten[ref]
        premisse = graaf.premisse(ref)

        sub_uitkomsten = [premisse_uitkomst(sub.ref) for sub in premisse.sub_premissen]

        genegeerd: list[tuple[str, str]] = []
        bijdragen: list[Bijdrage] = []

        heeft_bron = premisse.heeft_bron or bool(overschrijving.bron.get(ref, False))
        if not heeft_bron:
            for veld, score in (("thubut", premisse.thubut), ("dalalah", premisse.dalalah)):
                if score is not None:
                    genegeerd.append((veld, score.label))
            uitkomst = PremisseUitkomst(
                ref=ref,
                label=schaal.laagste,
                rationale=(
                    f"premisse '{ref}' noemt geen bron en heeft geen sub-premissen of beweerde "
                    "claim die haar dragen. Zonder bron is er niets vastgesteld"
                    + (
                        "; de handmatig aangeleverde score is daarom genegeerd en hier gemeld"
                        if genegeerd
                        else ""
                    )
                    + " (kernregel steun_en_bewijslast)"
                ),
                bijdragen=[],
                heeft_bron=False,
                raakt_bronloos=True,
                genegeerde_scores=genegeerd,
            )
            premisse_uitkomsten[ref] = uitkomst
            return uitkomst

        thubut_label = overschrijving.thubut.get(ref) or (
            premisse.thubut.label if premisse.thubut else None
        )
        dalalah_label = overschrijving.dalalah.get(ref) or (
            premisse.dalalah.label if premisse.dalalah else None
        )
        if thubut_label is not None:
            bijdragen.append(Bijdrage("premise", ref, "thubut", thubut_label))
        if dalalah_label is not None:
            bijdragen.append(Bijdrage("premise", ref, "dalalah", dalalah_label))
        for sub, sub_uitkomst in zip(premisse.sub_premissen, sub_uitkomsten, strict=True):
            bijdragen.append(Bijdrage("premise", sub.ref, None, sub_uitkomst.label))
        if premisse.asserts_claim:
            beweerd = claim_uitkomsten.get(premisse.asserts_claim)
            bijdragen.append(
                Bijdrage(
                    "claim",
                    premisse.asserts_claim,
                    None,
                    beweerd.label if beweerd else schaal.laagste,
                )
            )

        if not bijdragen:
            label = schaal.laagste
            rationale = (
                f"premisse '{ref}' heeft wel een bron maar geen aangeleverde sterkte; "
                "zonder meting blijft de sterkte onbepaald"
            )
        else:
            label = schaal.minimum(b.label for b in bijdragen)
            zwakke = [b for b in bijdragen if b.label == label]
            rationale = (
                f"de sterkte van premisse '{ref}' is het minimum over "
                f"{_som(bijdragen)}; het minimum wordt bepaald door {_som(zwakke)} "
                "(kernregel zwakste_schakel)"
            )

        raakt_bronloos = any(u.raakt_bronloos for u in sub_uitkomsten)
        if premisse.asserts_claim:
            beweerd = claim_uitkomsten.get(premisse.asserts_claim)
            raakt_bronloos = raakt_bronloos or (beweerd.onvoldoende_bewijs if beweerd else True)

        uitkomst = PremisseUitkomst(
            ref=ref,
            label=label,
            rationale=rationale,
            bijdragen=bijdragen,
            heeft_bron=True,
            raakt_bronloos=raakt_bronloos,
            genegeerde_scores=genegeerd,
        )
        premisse_uitkomsten[ref] = uitkomst
        return uitkomst

    def inferentie_uitkomst(ref: str) -> InferentieUitkomst:
        if ref in inferentie_uitkomsten:
            return inferentie_uitkomsten[ref]
        inferentie = graaf.inferenties[ref]
        analyse = vormanalyses[ref]

        if ref in overschrijving.inferentie:
            label = overschrijving.inferentie[ref]
            herkomst = "overschrijving"
            rationale = "hypothetische waarde voor de kantelpuntanalyse"
        elif analyse.status == "valid":
            label = schaal.hoogste
            herkomst = "formeel"
            rationale = (
                "de stap is formeel geldig: " + analyse.rationale + ". Geldigheid van de vorm zegt "
                "niets over de waarheid van de premissen (kernregel vorm_versus_waarheid)"
            )
        elif analyse.status == "invalid":
            label = schaal.laagste
            herkomst = "formeel"
            rationale = "de stap is formeel ongeldig: " + analyse.rationale
        elif inferentie.aangeleverde_sterkte is not None:
            label = inferentie.aangeleverde_sterkte.label
            herkomst = "aangeleverd"
            rationale = (
                "niet formeel getoetst; het label komt uit de invoer. "
                + inferentie.aangeleverde_sterkte.rationale
            )
        else:
            label = schaal.laagste
            herkomst = "onbepaald"
            rationale = "niet formeel getoetst en geen sterkte aangeleverd: " + analyse.rationale

        if herkomst == "formeel" and inferentie.aangeleverde_sterkte is not None:
            rationale += (
                f". De invoer leverde het label '{inferentie.aangeleverde_sterkte.label}' aan; "
                "de formele toets gaat daarvoor, want de geldigheid van een vorm is een "
                "vaststelling en geen inschatting"
            )

        gefaald = [
            vraag.sleutel
            for vraag in inferentie.kritische_vragen
            if (overschrijving.vraag.get(vraag.sleutel) or vraag.status) == "failed"
            and not vraag.beantwoord_door_motor
        ]
        if gefaald:
            label = schaal.laagste
            rationale += (
                ". Er is minstens één kritische vraag met de status 'gefaald'; zolang die staat, "
                "is het label van deze stap onbepaald. Anders zou de motor een stap sterk noemen "
                "die zij zelf als gebroken heeft gemarkeerd. Interim-regel voor fase 1: in fase 2 "
                "neemt de nederlaaggraaf deze rol over"
            )

        uitkomst = InferentieUitkomst(
            ref=ref,
            label=label,
            rationale=rationale,
            vormstatus=analyse.status,
            herkomst=herkomst,
            gefaalde_vragen=gefaald,
        )
        inferentie_uitkomsten[ref] = uitkomst
        return uitkomst

    def lijn_uitkomst(inferentie_ref: str) -> LijnUitkomst:
        inferentie = graaf.inferenties[inferentie_ref]
        stap = inferentie_uitkomst(inferentie_ref)
        elementen: list[Bijdrage] = []
        raakt_bronloos = False
        for premisse_ref in inferentie.van:
            uitkomst = premisse_uitkomst(premisse_ref)
            raakt_bronloos = raakt_bronloos or uitkomst.raakt_bronloos
            elementen.append(_diepste_zwakste(uitkomst, premisse_uitkomsten, schaal))
        elementen.append(Bijdrage("inference", inferentie_ref, "strength", stap.label))
        label = schaal.minimum(b.label for b in elementen)
        zwakste = [b for b in elementen if b.label == label]
        return LijnUitkomst(
            inferentie_ref=inferentie_ref,
            claim_ref=inferentie.naar,
            label=label,
            zwakste=zwakste[0] if zwakste else None,
            alle_zwakste=zwakste,
            raakt_bronloos=raakt_bronloos,
        )

    # Claims in een steunkring eerst: een claim die erop steunt, moet hun
    # uitkomst al kunnen aflezen in plaats van haar te moeten raden.
    for claim_ref in [*sorted(in_cykel), *volgorde]:
        if claim_ref in in_cykel:
            claim_uitkomsten[claim_ref] = ClaimUitkomst(
                ref=claim_ref,
                label=schaal.laagste,
                rationale=(
                    f"claim '{claim_ref}' ligt in een steunkring: zij komt langs haar eigen "
                    "premissen weer bij zichzelf uit. Zo'n keten draagt niets, en de motor "
                    "rekent haar niet door (kernregel steun_en_bewijslast)"
                ),
                bepalende_lijn=None,
                lijnen=list(graaf.lijnen_per_claim.get(claim_ref, [])),
                onvoldoende_bewijs=True,
                onvoldoende_uitleg=(
                    "de steun voor deze claim is circulair; er is geen onafhankelijke grond"
                ),
                in_cykel=True,
                zwakste=None,
                alle_zwakste=[],
            )
            continue

        lijn_refs = list(graaf.lijnen_per_claim.get(claim_ref, []))
        for inferentie_ref in lijn_refs:
            lijn_uitkomsten[inferentie_ref] = lijn_uitkomst(inferentie_ref)

        if not lijn_refs:
            claim_uitkomsten[claim_ref] = ClaimUitkomst(
                ref=claim_ref,
                label=schaal.laagste,
                rationale=(
                    f"claim '{claim_ref}' heeft geen enkele aangeleverde bewijslijn; er is niets "
                    "om aan af te wegen (kernregel steun_en_bewijslast)"
                ),
                bepalende_lijn=None,
                lijnen=[],
                onvoldoende_bewijs=True,
                onvoldoende_uitleg="er is geen bewijslijn aangeleverd voor deze claim",
                in_cykel=False,
                zwakste=None,
                alle_zwakste=[],
            )
            continue

        beste = max(lijn_refs, key=lambda ref: schaal.rang(lijn_uitkomsten[ref].label))
        label = lijn_uitkomsten[beste].label

        bronloze_lijnen = [ref for ref in lijn_refs if lijn_uitkomsten[ref].raakt_bronloos]
        onvoldoende = len(bronloze_lijnen) == len(lijn_refs)
        if onvoldoende:
            uitleg = (
                "elke aangeleverde bewijslijn voor deze claim bevat een premisse zonder bron; "
                "er is daarom onvoldoende bewijs om te scoren"
            )
        elif bronloze_lijnen:
            uitleg = (
                "een deel van de bewijslijnen bevat een premisse zonder bron: "
                + ", ".join(sorted(bronloze_lijnen))
                + ". Die lijnen dragen niet; de overige wel"
            )
        else:
            uitleg = "elke premisse in de aangeleverde lijnen noemt een bron"

        meerdere = len(lijn_refs) > 1
        rationale = (
            f"de sterkte van claim '{claim_ref}' is die van haar sterkste bewijslijn "
            f"('{beste}')."
            + (
                " Over lijnen heen geldt het maximum: een claim met één sluitende bewijslijn "
                "plus een slechte lijn is door die slechte lijn niet zwakker geworden. Binnen "
                "een lijn geldt het minimum, want een conclusie kan niet zekerder zijn dan haar "
                "zwakste schakel."
                if meerdere
                else " Binnen die lijn geldt het minimum over premissen en stap "
                "(kernregel zwakste_schakel)."
            )
        )

        claim_uitkomsten[claim_ref] = ClaimUitkomst(
            ref=claim_ref,
            label=label,
            rationale=rationale,
            bepalende_lijn=beste,
            lijnen=lijn_refs,
            onvoldoende_bewijs=onvoldoende,
            onvoldoende_uitleg=uitleg,
            in_cykel=False,
            zwakste=lijn_uitkomsten[beste].zwakste,
            alle_zwakste=lijn_uitkomsten[beste].alle_zwakste,
        )

    for ref in graaf.volgorde_premissen:
        premisse_uitkomst(ref)
    for ref in graaf.inferenties:
        inferentie_uitkomst(ref)

    bronloos = [ref for ref, uitkomst in premisse_uitkomsten.items() if not uitkomst.heeft_bron]

    return Berekening(
        premissen=premisse_uitkomsten,
        inferenties=inferentie_uitkomsten,
        lijnen=lijn_uitkomsten,
        claims=claim_uitkomsten,
        cykels=cykels,
        bronloze_premissen=sorted(bronloos),
    )


def _som(bijdragen: list[Bijdrage]) -> str:
    delen = []
    for bijdrage in bijdragen:
        naam = f"{bijdrage.soort} '{bijdrage.ref}'"
        if bijdrage.veld:
            naam += f" ({bijdrage.veld})"
        delen.append(f"{naam} = {bijdrage.label}")
    return "; ".join(delen)


def _diepste_zwakste(
    uitkomst: PremisseUitkomst,
    alle: dict[str, PremisseUitkomst],
    schaal: Schaal,
) -> Bijdrage:
    """Wijs het diepste element aan dat de sterkte van een premisse bepaalt."""
    for bijdrage in uitkomst.bijdragen:
        if bijdrage.label != uitkomst.label:
            continue
        if bijdrage.soort == "premise" and bijdrage.veld is None and bijdrage.ref in alle:
            return _diepste_zwakste(alle[bijdrage.ref], alle, schaal)
        return bijdrage
    return Bijdrage("premise", uitkomst.ref, None, uitkomst.label)
