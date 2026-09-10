"""Stap 1: ontleden. De aangeleverde structuur wordt een gecontroleerde graaf.

Elke verwijzing moet oplosbaar zijn en elke vocabulairewaarde moet in haar
lookup-tabel staan. Een verwijzing die nergens heen wijst, is een oordeel over
iets ongedefinieerds; dat weigert de motor op grond van de kernregel
``oordeel_vereist_begrip``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.model import LOOKUP_KLASSEN
from ..fouten import InvoerFout, OnbekendeLookupwaarde, OngedefinieerdeVerwijzing
from ..logica import vorm as vormlogica
from ..schemas.invoer import InzendingInvoer, PremisseInvoer, ScoreInvoer


@dataclass(frozen=True)
class Vocabulaires:
    """De toegestane waarden per vocabulaire, geladen uit de database."""

    waarden: dict[str, frozenset[str]]

    @classmethod
    def uit_db(cls, sessie: Session) -> Vocabulaires:
        geladen: dict[str, frozenset[str]] = {}
        for naam, klasse in LOOKUP_KLASSEN.items():
            rijen = sessie.execute(select(klasse.key).where(klasse.actief.is_(True))).scalars()
            geladen[naam] = frozenset(rijen)
        return cls(waarden=geladen)

    def controleer(self, vocabulaire: str, waarde: str | None, waar: str) -> str | None:
        if waarde is None:
            return None
        toegestaan = self.waarden.get(vocabulaire, frozenset())
        if waarde not in toegestaan:
            raise OnbekendeLookupwaarde(
                f"{waar}: '{waarde}' staat niet in de lookup-tabel '{vocabulaire}'. "
                f"Bekende waarden: {', '.join(sorted(toegestaan)) or '(geen)'}. "
                "Voeg een rij toe aan de lookup-tabel om deze waarde toe te laten."
            )
        return waarde


@dataclass(frozen=True)
class Score:
    label: str
    rationale: str
    computed_by: str
    version: str
    instrument: str | None = None

    def als_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "rationale": self.rationale,
            "computed_by": self.computed_by,
            "version": self.version,
            "instrument": self.instrument,
        }


@dataclass(frozen=True)
class Citaat:
    source_ref: str | None
    verification_status: str


@dataclass(frozen=True)
class Herkomst:
    kind: str
    detail: dict[str, Any] | None
    retrieval_ref: str | None


@dataclass(frozen=True)
class Status:
    label: str
    opposition: str


@dataclass
class Premisse:
    ref: str
    tekst: str
    type: str | None
    explicit: bool
    provenance: Herkomst
    citation: Citaat
    thubut: Score | None
    dalalah: Score | None
    status: Status | None
    sub_premissen: list[Premisse]
    instrument_output: dict[str, Any] | None
    vorm: dict[str, Any] | None
    termen: tuple[str, ...]
    asserts_claim: str | None
    proposed_by: str
    confirmed: bool
    ouder_ref: str | None = None

    @property
    def heeft_bron(self) -> bool:
        bron = (self.citation.source_ref or "").strip()
        return bool(bron) or bool(self.sub_premissen) or bool(self.asserts_claim)


@dataclass
class KritischeVraag:
    sleutel: str
    vraag: str
    status: str
    effect: str
    toelichting: str | None
    # Volgnummer van de basisvraag waarop deze vraag antwoord geeft; leeg bij
    # een eigen vraag die niet in de geseede vragenset staat.
    template: str | None = None
    beantwoord_door_motor: bool = False
    herkomst: str = "invoer"


@dataclass
class Inferentie:
    ref: str
    van: tuple[str, ...]
    naar: str
    scheme: str | None
    interpretation_ref: str | None
    kritische_vragen: list[KritischeVraag]
    aangeleverde_sterkte: Score | None
    proposed_by: str
    confirmed: bool


@dataclass
class Claim:
    ref: str
    tekst: str
    vorm: dict[str, Any] | None
    termen: tuple[str, ...]


@dataclass
class Graaf:
    claims: dict[str, Claim]
    premissen: dict[str, Premisse]
    inferenties: dict[str, Inferentie]
    lijnen_per_claim: dict[str, list[str]]
    profielnaam: str
    profielversie: str | None
    competentieniveau: str
    gebruiksvorm: str
    kop: dict[str, Any]
    volgorde_claims: tuple[str, ...] = ()
    volgorde_premissen: tuple[str, ...] = ()

    def premisse(self, ref: str) -> Premisse:
        try:
            return self.premissen[ref]
        except KeyError as fout:
            raise OngedefinieerdeVerwijzing(f"premisse '{ref}' bestaat niet") from fout

    def claim(self, ref: str) -> Claim:
        try:
            return self.claims[ref]
        except KeyError as fout:
            raise OngedefinieerdeVerwijzing(f"claim '{ref}' bestaat niet") from fout


def _score(
    invoer: ScoreInvoer | None, vocab: Vocabulaires, waar: str, standaardversie: str
) -> Score | None:
    if invoer is None:
        return None
    vocab.controleer("strength_label", invoer.label, waar)
    vocab.controleer("score_source", invoer.computed_by, waar)
    return Score(
        label=invoer.label,
        rationale=invoer.rationale,
        computed_by=invoer.computed_by,
        version=invoer.version or standaardversie,
        instrument=invoer.instrument,
    )


def _vorm(ruw: Any, waar: str) -> dict[str, Any] | None:
    if ruw is None:
        return None
    try:
        return vormlogica.normaliseer(ruw)
    except vormlogica.VormFout as fout:
        raise InvoerFout(f"{waar}: {fout}") from fout


def _bouw_premisse(
    invoer: PremisseInvoer,
    vocab: Vocabulaires,
    verzameling: dict[str, Premisse],
    volgorde: list[str],
    standaardversie: str,
    ouder_ref: str | None = None,
) -> Premisse:
    waar = f"premisse '{invoer.id}'"
    if invoer.id in verzameling:
        raise InvoerFout(f"{waar}: deze verwijzing komt meer dan één keer voor")
    vocab.controleer("premise_type", invoer.type, waar)
    vocab.controleer("provenance_kind", invoer.provenance.kind, waar + " (provenance)")
    vocab.controleer("proposed_by", invoer.proposed_by, waar)
    citaat = invoer.citation
    # Ook de standaardwaarde gaat langs de lookup: anders zou één waarde uit het
    # vocabulaire buiten de data om gelden.
    vocab.controleer(
        "verification_status",
        citaat.verification_status if citaat else "unverified",
        waar + " (citaat)",
    )

    premisse = Premisse(
        ref=invoer.id,
        tekst=invoer.text,
        type=invoer.type,
        explicit=invoer.explicit,
        provenance=Herkomst(
            kind=invoer.provenance.kind,
            detail=invoer.provenance.detail,
            retrieval_ref=invoer.provenance.retrieval_ref,
        ),
        citation=Citaat(
            source_ref=citaat.source_ref if citaat else None,
            verification_status=citaat.verification_status if citaat else "unverified",
        ),
        thubut=_score(invoer.thubut, vocab, waar + " (thubut)", standaardversie),
        dalalah=_score(invoer.dalalah, vocab, waar + " (dalalah)", standaardversie),
        status=(
            Status(label=invoer.status.label, opposition=invoer.status.opposition)
            if invoer.status
            else None
        ),
        sub_premissen=[],
        instrument_output=invoer.instrument_output,
        vorm=_vorm(invoer.form, waar),
        termen=tuple(invoer.terms),
        asserts_claim=invoer.asserts_claim,
        proposed_by=invoer.proposed_by,
        confirmed=invoer.confirmed,
        ouder_ref=ouder_ref,
    )
    verzameling[invoer.id] = premisse
    volgorde.append(invoer.id)
    for sub in invoer.sub_premises:
        premisse.sub_premissen.append(
            _bouw_premisse(sub, vocab, verzameling, volgorde, standaardversie, ouder_ref=invoer.id)
        )
    return premisse


def bouw(invoer: InzendingInvoer, vocab: Vocabulaires, standaardversie: str) -> Graaf:
    """Zet gecontroleerde invoer om in de graaf waarover de motor rekent."""
    vocab.controleer("use_form", invoer.use_form, "inzending (use_form)")

    claims: dict[str, Claim] = {}
    for claiminvoer in invoer.claims:
        if claiminvoer.id in claims:
            raise InvoerFout(
                f"claim '{claiminvoer.id}': deze verwijzing komt meer dan één keer voor"
            )
        claims[claiminvoer.id] = Claim(
            ref=claiminvoer.id,
            tekst=claiminvoer.text,
            vorm=_vorm(claiminvoer.form, f"claim '{claiminvoer.id}'"),
            termen=tuple(claiminvoer.terms),
        )

    premissen: dict[str, Premisse] = {}
    volgorde_premissen: list[str] = []
    for premisseinvoer in invoer.premises:
        _bouw_premisse(premisseinvoer, vocab, premissen, volgorde_premissen, standaardversie)

    for premisse in premissen.values():
        if premisse.asserts_claim is not None and premisse.asserts_claim not in claims:
            raise OngedefinieerdeVerwijzing(
                f"premisse '{premisse.ref}' beweert claim '{premisse.asserts_claim}', "
                "maar die claim is niet aangeleverd"
            )

    inferenties: dict[str, Inferentie] = {}
    lijnen: dict[str, list[str]] = {ref: [] for ref in claims}
    for inferentieinvoer in invoer.inferences:
        waar = f"inferentie '{inferentieinvoer.id}'"
        if inferentieinvoer.id in inferenties:
            raise InvoerFout(f"{waar}: deze verwijzing komt meer dan één keer voor")
        vocab.controleer("scheme", inferentieinvoer.scheme, waar)
        vocab.controleer("proposed_by", inferentieinvoer.proposed_by, waar)
        if inferentieinvoer.naar not in claims:
            raise OngedefinieerdeVerwijzing(
                f"{waar}: de conclusie '{inferentieinvoer.naar}' is geen aangeleverde claim"
            )
        if not inferentieinvoer.van:
            raise InvoerFout(f"{waar}: een stap zonder premissen draagt niets")
        for premisse_ref in inferentieinvoer.van:
            if premisse_ref not in premissen:
                raise OngedefinieerdeVerwijzing(
                    f"{waar}: premisse '{premisse_ref}' is niet aangeleverd"
                )

        vragen: list[KritischeVraag] = []
        for nummer, vraaginvoer in enumerate(inferentieinvoer.critical_questions):
            vocab.controleer("critical_question_status", vraaginvoer.status, waar + " (vraag)")
            vocab.controleer("critical_question_effect", vraaginvoer.effect, waar + " (vraag)")
            vragen.append(
                KritischeVraag(
                    sleutel=f"{inferentieinvoer.id}#{nummer}",
                    vraag=vraaginvoer.question,
                    status=vraaginvoer.status,
                    effect=vraaginvoer.effect,
                    toelichting=vraaginvoer.toelichting,
                    template=vraaginvoer.template,
                )
            )

        inferenties[inferentieinvoer.id] = Inferentie(
            ref=inferentieinvoer.id,
            van=tuple(inferentieinvoer.van),
            naar=inferentieinvoer.naar,
            scheme=inferentieinvoer.scheme,
            interpretation_ref=inferentieinvoer.interpretation_ref,
            kritische_vragen=vragen,
            aangeleverde_sterkte=_score(
                inferentieinvoer.strength, vocab, waar + " (sterkte)", standaardversie
            ),
            proposed_by=inferentieinvoer.proposed_by,
            confirmed=inferentieinvoer.confirmed,
        )
        lijnen[inferentieinvoer.naar].append(inferentieinvoer.id)

    return Graaf(
        claims=claims,
        premissen=premissen,
        inferenties=inferenties,
        lijnen_per_claim=lijnen,
        profielnaam=invoer.profile,
        profielversie=invoer.profile_version,
        competentieniveau=invoer.competence_level,
        gebruiksvorm=invoer.use_form,
        kop={
            "id": invoer.submission.id,
            "title": invoer.submission.title,
            "language": invoer.submission.language,
        },
        volgorde_claims=tuple(claims),
        volgorde_premissen=tuple(volgorde_premissen),
    )


def claim_afhankelijkheden(graaf: Graaf) -> dict[str, set[str]]:
    """Welke claims een claim nodig heeft, via premissen die een claim beweren."""
    afhankelijk: dict[str, set[str]] = {ref: set() for ref in graaf.claims}
    for claim_ref, inferentie_refs in graaf.lijnen_per_claim.items():
        for inferentie_ref in inferentie_refs:
            for premisse_ref in graaf.inferenties[inferentie_ref].van:
                for bewering in _beweerde_claims(graaf, premisse_ref):
                    afhankelijk[claim_ref].add(bewering)
    return afhankelijk


def _beweerde_claims(graaf: Graaf, premisse_ref: str) -> set[str]:
    premisse = graaf.premisse(premisse_ref)
    gevonden: set[str] = set()
    if premisse.asserts_claim:
        gevonden.add(premisse.asserts_claim)
    for sub in premisse.sub_premissen:
        gevonden |= _beweerde_claims(graaf, sub.ref)
    return gevonden


def zoek_cykels(afhankelijk: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """Zoek de steunkringen in de steunrelatie tussen claims.

    Elke groep claims die elkaar wederzijds bereiken vormt één kring. Een claim
    die zichzelf steunt vormt er ook een.

    De implementatie volgt Tarjan: sterk samenhangende componenten. Een simpele
    diepteweergave met een 'al bezocht'-markering is hier niet genoeg. Zij vindt
    per zoektocht wel een kring, maar mist knopen die alleen via een al afgeronde
    tak in een kring liggen. Voor deze motor is dat geen detail: een gemiste
    kring betekent dat een claim die op zichzelf steunt een positief label krijgt
    in plaats van een cirkelredenering.
    """
    index_van: dict[str, int] = {}
    laagste: dict[str, int] = {}
    op_stapel: dict[str, bool] = {}
    stapel: list[str] = []
    teller = 0
    componenten: list[list[str]] = []

    def sterk_verbonden(start: str) -> None:
        nonlocal teller
        werk: list[tuple[str, list[str]]] = [(start, sorted(afhankelijk.get(start, set())))]
        index_van[start] = laagste[start] = teller
        teller += 1
        stapel.append(start)
        op_stapel[start] = True

        while werk:
            knoop, resterend = werk[-1]
            if resterend:
                volgende = resterend.pop(0)
                if volgende not in index_van:
                    index_van[volgende] = laagste[volgende] = teller
                    teller += 1
                    stapel.append(volgende)
                    op_stapel[volgende] = True
                    werk.append((volgende, sorted(afhankelijk.get(volgende, set()))))
                elif op_stapel.get(volgende):
                    laagste[knoop] = min(laagste[knoop], index_van[volgende])
                continue

            werk.pop()
            if werk:
                ouder = werk[-1][0]
                laagste[ouder] = min(laagste[ouder], laagste[knoop])
            if laagste[knoop] == index_van[knoop]:
                component: list[str] = []
                while True:
                    lid = stapel.pop()
                    op_stapel[lid] = False
                    component.append(lid)
                    if lid == knoop:
                        break
                componenten.append(sorted(component))

    for knoop in sorted(afhankelijk):
        if knoop not in index_van:
            sterk_verbonden(knoop)

    kringen: list[tuple[str, ...]] = []
    for component in componenten:
        if len(component) > 1:
            kringen.append(tuple(component))
        else:
            enkel = component[0]
            if enkel in afhankelijk.get(enkel, set()):
                kringen.append((enkel,))
    return sorted(kringen)


def steunkringen(graaf: Graaf) -> list[tuple[str, ...]]:
    """De steunkringen tussen claims.

    Dit is een eigenschap van de ontleding, niet van de zekerheidsberekening.
    Zij wordt daarom in stap 1 bepaald, zodat stap 7 haar kan gebruiken zonder
    de uitkomst van stap 10 te raadplegen (B2: geen stap raadpleegt een latere).
    """
    return zoek_cykels(claim_afhankelijkheden(graaf))


def topologische_volgorde(afhankelijk: dict[str, set[str]], in_cykel: set[str]) -> list[str]:
    """Claims in de volgorde waarin ze berekend kunnen worden."""
    klaar: list[str] = []
    gezien: set[str] = set()

    def loop(knoop: str) -> None:
        if knoop in gezien or knoop in in_cykel:
            return
        gezien.add(knoop)
        for volgende in sorted(afhankelijk.get(knoop, set())):
            loop(volgende)
        klaar.append(knoop)

    for knoop in sorted(afhankelijk):
        loop(knoop)
    return klaar
