"""De motor. Fase 1 draait de stappen 1, 2, 6, 7, 10, 11 en 12 uit §6.

De vaste evaluatievolgorde (B2) wordt aangehouden: geen stap raadpleegt een
latere stap. De formele vormtoets hoort bij stap 2, omdat het blootleggen van
een mogelijk verzwegen premisse haar nodig heeft; stap 6 hergebruikt die uitkomst
en voegt er geen nieuwe toets aan toe.

Wat fase 1 met opzet niet doet, staat in elk rapport onder ``voorbehouden``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import CONTRACT_VERSIE, GEBOUWDE_FASE, INVOERSCHEMA_VERSIE, MOTOR_VERSIE
from ..contract import verifieer
from ..db.model import (
    LOOKUP_KLASSEN,
    Assessment,
    AssessmentDependency,
    AssessmentFallacy,
    AssessmentOpenQuestion,
    AssessmentTippingPoint,
    AssessmentUnstatedPremise,
    Claim as ClaimRij,
    CompetenceLevel,
    Inference as InferenceRij,
    InferenceCriticalQuestion,
    InferencePremise,
    KernelRule,
    Premise as PremiseRij,
    Profile,
    ProfileQaida,
    SchemeCriticalQuestion,
    Score as ScoreRij,
    Submission,
)
from ..db.registry import haal_profiel, regelset_versie, schrijf_audit
from ..fouten import (
    InvoerFout,
    OnbekendeLookupwaarde,
    OnbepaaldeProfielinstelling,
    OntbrekendeKern,
)
from ..interim import INTERIM_REGELS
from ..labels import Schaal
from ..logica import vorm as vormlogica
from ..logica.vorm import VormAnalyse
from ..schemas.invoer import InzendingInvoer
from . import kantelpunten as kantelmodule
from .berekening import Berekening, bereken
from .bevindingen import DrogredenBevinding, VerzwegenVoorstel
from .graaf import Graaf, KritischeVraag, Premisse, Vocabulaires, bouw, steunkringen
from .rapport import bouw_beoordeling

VOORBEHOUDEN_FASE1 = (
    "Fase 1. De motor draait uitsluitend op de kern; er zijn geen inhoudelijke regels geladen.",
    "Van de vier gebruiksvormen voert de motor alleen 'toetsen' uit. Vergelijken, aanvallen en "
    "verdedigen bestaan in het schema en worden geweigerd zolang ze niet gebouwd zijn.",
    "Premissesterkte komt uit handmatige invoer. Meetinstrumenten komen in fase 3.",
    "Er zijn geen qawa'id en geen profielinstellingen die het oordeel sturen.",
    "De interpretatielaag draait niet. Een aangeleverde interpretation_ref wordt vastgelegd maar "
    "nog niet afgedwongen; dat gebeurt in fase 4.",
    "Statusafleiding, bijvoorbeeld naskh uit zes voorwaarden, draait niet.",
    "Reikwijdtevergelijking, conflictresolutie en de nederlaaggraaf draaien niet.",
    "Verhoging van het label door convergente onafhankelijke steun wordt niet toegepast.",
    "Er worden geen zekerheidsplafonds per premissetype toegepast; die komen in fase 3.",
    "Er komt geen taalmodel aan te pas. Alle structuur is door de indiener aangeleverd.",
    "Dit instrument beoordeelt de kwaliteit van bewijsvoering. Het beoordeelt geen waarheid en "
    "geen personen.",
)


# De kernregels waarop de motor in fase 1 daadwerkelijk steunt. Ontbreekt er
# een, dan weigert de motor te rekenen in plaats van door te gaan met een kern
# die niet meer compleet is (randvoorwaarde 2.3: de motor weigert kernregels te
# laten vallen).
VEREISTE_KERNREGELS = frozenset(
    {
        "non_contradictie",
        "oordeel_vereist_begrip",
        "zwakste_schakel",
        "vorm_versus_waarheid",
        "steun_en_bewijslast",
    }
)

# Toetsen die de motor zelf kan uitvoeren en waarmee een kritische vraag
# beantwoord kan worden. Een sjabloon dat een andere capaciteit noemt, is een
# fout in de data en geen stilzwijgend genegeerde regel.
MOTORCAPACITEITEN = frozenset({"form_validity"})

# Vocabulairewaarden waar de motor bij het rekenen op steunt. Ze staan als rij
# in de database, maar de motor noemt ze bij naam: 'failed' plafonneert het
# label van een stap, 'valid' en 'invalid' komen uit de vormtoets. Wordt zo'n
# rij hernoemd of op inactief gezet, dan zou de bijbehorende regel stilzwijgend
# ophouden te werken. De motor controleert daarom bij het opstarten dat elke
# sleutel waarop zij steunt bestaat en actief is, en zegt het anders.
VEREISTE_VOCABULAIREWAARDEN: dict[str, frozenset[str]] = {
    "critical_question_status": frozenset({"answered", "unanswered", "failed"}),
    "critical_question_effect": frozenset({"undercut", "undermine", "none"}),
    "critical_question_origin": frozenset({"base", "profile", "input"}),
    "form_status": frozenset({"valid", "invalid", "not_testable"}),
    "fallacy_type": frozenset(
        {
            "affirming_the_consequent",
            "denying_the_antecedent",
            "undistributed_middle",
            "circular_reasoning",
            "invalid_form_unnamed",
            "contradictory_premises",
        }
    ),
    "unstated_premise_basis": frozenset({"form_completion", "term_coverage"}),
    "score_source": frozenset({"engine_kernel"}),
    "proposed_by": frozenset({"engine"}),
    "tipping_direction": frozenset({"upward", "downward"}),
    "node_kind": frozenset({"premise", "claim", "inference", "critical_question"}),
}

# Wat de drogredenscan van fase 1 wél en niet dekt. Een lege lijst bevindingen
# betekent zonder deze toelichting iets anders dan zij zegt.
DROGREDENSCAN_FASE1 = {
    "getoetst": [
        "bevestigen van het consequens",
        "ontkennen van het antecedent",
        "onverdeelde middenterm",
        "cirkelredenering, zowel in de vorm als in de steunrelatie tussen claims",
        "elkaar tegensprekende premissen",
        "overige ongeldige vormen zonder eigen naam",
    ],
    "niet_getoetst": [
        "informele drogredenen zoals stroman, vals dilemma, beroep op onwetendheid en "
        "beroep op nadelige gevolgen; die vallen vaak samen met een schema waarvan de "
        "kritische vragen falen en komen in een latere fase",
    ],
    "toelichting": (
        "een lege lijst drogredenen betekent dus: geen van de hierboven getoetste vormen "
        "aangetroffen, niet dat er geen drogreden in de tekst zit"
    ),
}


class Motor:
    """De rekenende laag. Leest regels als data, rekent zelf niets inhoudelijks."""

    def __init__(self, sessie: Session) -> None:
        self.sessie = sessie
        self.schaal = Schaal.uit_db(sessie)
        self.vocab = Vocabulaires.uit_db(sessie)
        self.kernregels = {
            rij.key: {
                "statement_nl": rij.statement_nl,
                "self_refutation_argument": rij.self_refutation_argument,
                "version": rij.version,
            }
            for rij in sessie.execute(select(KernelRule)).scalars()
        }
        for vocabulaire, sleutels in VEREISTE_VOCABULAIREWAARDEN.items():
            ontbreekt = sleutels - self.vocab.waarden.get(vocabulaire, frozenset())
            if ontbreekt:
                raise OnbekendeLookupwaarde(
                    f"de motor steunt op de waarden {', '.join(sorted(ontbreekt))} in de lookup "
                    f"'{vocabulaire}', maar die bestaan daar niet of staan op inactief. "
                    "Regels zijn data, maar de motor noemt deze waarden bij naam; zou zij ze "
                    "stil missen, dan zou de bijbehorende regel zonder melding ophouden te "
                    "werken."
                )
        ontbrekend = VEREISTE_KERNREGELS - set(self.kernregels)
        if ontbrekend:
            raise OntbrekendeKern(
                "de motor steunt op kernregels die niet in de database staan: "
                + ", ".join(sorted(ontbrekend))
                + ". De kern is niet iets waar de motor omheen kan rekenen; zonder deze "
                "records weigert zij te oordelen (randvoorwaarde 2.3)."
            )
        self.kernregel_van_drogreden = self._kernregel_index("fallacy_type")
        self.kernregel_van_basis = self._kernregel_index("unstated_premise_basis")

    def _kernregel_van(self, index: dict[str, str], sleutel: str, vocabulaire: str) -> str:
        """Welke kernregel een soort bevinding draagt, staat in de data.

        Zwijgt de lookup erover, dan is dat een gat in de data en geen reden om
        er in code een te kiezen. Een stille terugval zou de bewering dat deze
        koppeling data is, onwaar maken.
        """
        kernregel = index.get(sleutel)
        if not kernregel:
            raise OnbekendeLookupwaarde(
                f"de rij '{sleutel}' in de lookup '{vocabulaire}' noemt geen kernregel. "
                "Welke kernregel een soort bevinding draagt, staat in de data; de motor "
                "kiest er zelf geen."
            )
        return kernregel

    def _kernregel_index(self, vocabulaire: str) -> dict[str, str]:
        klasse = LOOKUP_KLASSEN[vocabulaire]
        rijen = self.sessie.execute(select(klasse.key, klasse.kernregel)).all()
        return {key: kernregel for key, kernregel in rijen if kernregel}

    # ------------------------------------------------------------------
    # Stap 2: vormtoets en mogelijk verzwegen premissen
    # ------------------------------------------------------------------

    def _vormanalyses(self, graaf: Graaf) -> dict[str, VormAnalyse]:
        analyses: dict[str, VormAnalyse] = {}
        for ref, inferentie in graaf.inferenties.items():
            premisse_vormen = [graaf.premisse(p).vorm for p in inferentie.van]
            conclusie = graaf.claim(inferentie.naar).vorm
            analyses[ref] = vormlogica.analyseer(premisse_vormen, conclusie, list(inferentie.van))
        return analyses

    def _verzwegen_premissen(
        self, graaf: Graaf, analyses: dict[str, VormAnalyse]
    ) -> list[VerzwegenVoorstel]:
        voorstellen: list[VerzwegenVoorstel] = []
        for ref, inferentie in graaf.inferenties.items():
            analyse = analyses[ref]
            for kandidaat in analyse.kandidaten:
                voorstellen.append(
                    VerzwegenVoorstel(
                        inferentie_ref=ref,
                        voorstel=f"mogelijk verzwegen premisse: {kandidaat.tekst}",
                        vorm=kandidaat.vorm,
                        basis=kandidaat.basis,
                        rationale=(
                            "interim-regel §4.5. toets: vormaanvulling. " + kandidaat.rationale
                        ),
                        kernregel=self._kernregel_van(
                            self.kernregel_van_basis, kandidaat.basis, "unstated_premise_basis"
                        ),
                    )
                )
            if analyse.status != "not_testable":
                continue
            conclusietermen = set(graaf.claim(inferentie.naar).termen)
            if not conclusietermen:
                continue
            gedekt: set[str] = set()
            for premisse_ref in inferentie.van:
                gedekt |= self._termen_van(graaf.premisse(premisse_ref))
            ongedekt = sorted(conclusietermen - gedekt)
            for term in ongedekt:
                voorstellen.append(
                    VerzwegenVoorstel(
                        inferentie_ref=ref,
                        voorstel=(
                            f"mogelijk verzwegen premisse: iets dat '{term}' met de aangevoerde "
                            "premissen verbindt"
                        ),
                        vorm=None,
                        basis="term_coverage",
                        kernregel=self._kernregel_van(
                            self.kernregel_van_basis, "term_coverage", "unstated_premise_basis"
                        ),
                        rationale=(
                            "interim-regel §4.5. toets: termdekking. De term "
                            f"'{term}' staat in de conclusie en in "
                            "geen van de aangevoerde premissen. Termdekking is een heuristiek en "
                            "geen bewijs: de verbinding kan ook in de woorden zelf besloten "
                            "liggen. De motor stelt daarom een aanname voor en stelt geen gat vast"
                        ),
                    )
                )
        return voorstellen

    def _termen_van(self, premisse: Premisse) -> set[str]:
        gevonden = set(premisse.termen)
        for sub in premisse.sub_premissen:
            gevonden |= self._termen_van(sub)
        return gevonden

    # ------------------------------------------------------------------
    # Stap 6: kritische vragen bij elke stap
    # ------------------------------------------------------------------

    def _vul_kritische_vragen(
        self, graaf: Graaf, analyses: dict[str, VormAnalyse], profiel: Profile
    ) -> None:
        for ref, inferentie in graaf.inferenties.items():
            analyse = analyses[ref]
            eigen_vragen = list(inferentie.kritische_vragen)
            per_template: dict[str, KritischeVraag] = {}
            dubbel: list[KritischeVraag] = []
            for vraag in eigen_vragen:
                if vraag.template is None:
                    continue
                if vraag.template in per_template:
                    # Twee antwoorden op dezelfde basisvraag. Het tweede mag niet
                    # verdwijnen: dat zou een geldige defeater onderdrukken
                    # (§4.3). Het wordt een eigen vraag naast de basisvraag.
                    dubbel.append(vraag)
                else:
                    per_template[vraag.template] = vraag
            samengesteld: list[KritischeVraag] = []
            gebruikte_templates: set[str] = set()

            for sjabloon in self._sjablonen(inferentie.scheme, profiel):
                sleutel = f"{ref}#{sjabloon.volgnummer}"
                aangeleverd = per_template.get(sjabloon.volgnummer)
                status = aangeleverd.status if aangeleverd else "unanswered"
                effect = aangeleverd.effect if aangeleverd else sjabloon.standaard_effect
                toelichting = aangeleverd.toelichting if aangeleverd else None
                door_motor = False

                capaciteit = sjabloon.beantwoordbaar_door_motor
                if capaciteit is not None and capaciteit not in MOTORCAPACITEITEN:
                    raise OnbekendeLookupwaarde(
                        f"kritische vraag '{sjabloon.volgnummer}' bij schema "
                        f"'{sjabloon.scheme}' noemt de motorcapaciteit '{capaciteit}', die de "
                        "motor niet heeft. Zou de motor dat stil negeren, dan zou een typefout "
                        "de bescherming tegen dubbel tellen uitschakelen zonder melding. "
                        f"Bekende capaciteiten: {', '.join(sorted(MOTORCAPACITEITEN))}."
                    )
                if capaciteit == "form_validity" and analyse.status in {"valid", "invalid"}:
                    nieuwe_status = "answered" if analyse.status == "valid" else "failed"
                    door_motor = True
                    extra = (
                        "de motor heeft deze vraag zelf beantwoord met de formele vormtoets. "
                        "Zij levert daarom geen apart effect op het label: het effect zit al in "
                        "de uitkomst van die toets, en dubbel tellen is verboden"
                    )
                    if aangeleverd and aangeleverd.status != nieuwe_status:
                        extra += (
                            f". De invoer gaf hier '{aangeleverd.status}' op; de formele toets "
                            "gaat voor"
                        )
                    toelichting = f"{toelichting}. {extra}" if toelichting else extra
                    status = nieuwe_status

                if aangeleverd:
                    gebruikte_templates.add(sjabloon.volgnummer)
                samengesteld.append(
                    KritischeVraag(
                        sleutel=sleutel,
                        vraag=aangeleverd.vraag if aangeleverd else sjabloon.vraag_nl,
                        status=status,
                        effect=effect,
                        toelichting=toelichting,
                        beantwoord_door_motor=door_motor,
                        herkomst=sjabloon.origin,
                    )
                )

            for nummer, vraag in enumerate(eigen_vragen):
                if (
                    vraag.template is not None
                    and vraag.template in gebruikte_templates
                    and all(vraag is not ander for ander in dubbel)
                ):
                    continue
                samengesteld.append(
                    KritischeVraag(
                        sleutel=f"{ref}#eigen{nummer}",
                        vraag=vraag.vraag,
                        status=vraag.status,
                        effect=vraag.effect,
                        toelichting=vraag.toelichting,
                        herkomst="input",
                    )
                )

            inferentie.kritische_vragen = samengesteld

    def _sjablonen(self, scheme: str | None, profiel: Profile) -> list[SchemeCriticalQuestion]:
        if scheme is None:
            return []
        vraag = (
            select(SchemeCriticalQuestion)
            .where(SchemeCriticalQuestion.scheme == scheme)
            .where(
                or_(
                    SchemeCriticalQuestion.profile_id.is_(None),
                    SchemeCriticalQuestion.profile_id == profiel.id,
                )
            )
            .order_by(SchemeCriticalQuestion.volgnummer)
        )
        return list(self.sessie.execute(vraag).scalars())

    # ------------------------------------------------------------------
    # Stap 7: formele drogredenen
    # ------------------------------------------------------------------

    def _drogredenen(
        self,
        graaf: Graaf,
        analyses: dict[str, VormAnalyse],
        cykels: list[tuple[str, ...]],
    ) -> list[DrogredenBevinding]:
        gevonden: list[DrogredenBevinding] = []
        for ref, analyse in analyses.items():
            for drogreden in analyse.drogredenen:
                gevonden.append(
                    DrogredenBevinding(
                        soort=drogreden.soort,
                        element_soort="inference",
                        element_ref=ref,
                        rationale=drogreden.rationale,
                        kernregel=self._kernregel_van(
                            self.kernregel_van_drogreden, drogreden.soort, "fallacy_type"
                        ),
                    )
                )
        for kring in cykels:
            # Elke claim in de kring krijgt de bevinding in haar eigen rapport.
            # Dat is geen dubbel tellen: het label wordt er niet door verlaagd,
            # en zonder dit zou een claim in een steunkring er schoon uitzien.
            for claim_ref in dict.fromkeys(kring):
                gevonden.append(
                    DrogredenBevinding(
                        soort="circular_reasoning",
                        element_soort="claim",
                        element_ref=claim_ref,
                        rationale=(
                            "de steun voor deze claim loopt langs haar eigen premissen weer bij "
                            "zichzelf uit. De claims die elkaar wederzijds dragen zijn: "
                            + ", ".join(kring)
                        ),
                        kernregel=self._kernregel_van(
                            self.kernregel_van_drogreden, "circular_reasoning", "fallacy_type"
                        ),
                    )
                )
        return _ontdubbel(gevonden)

    # ------------------------------------------------------------------
    # Uitvoeren
    # ------------------------------------------------------------------

    def beoordeel(
        self, ruwe_invoer: dict[str, Any], *, actor: str = "onbekend", opslaan: bool = True
    ) -> dict[str, Any]:
        invoer = InzendingInvoer.model_validate(ruwe_invoer)
        graaf = bouw(invoer, self.vocab, MOTOR_VERSIE)  # stap 1
        self._weiger_niet_verwerkte_velden(graaf)
        self._weiger_niet_gebouwde_gebruiksvorm(graaf.gebruiksvorm)
        profiel = haal_profiel(self.sessie, invoer.profile, invoer.profile_version)
        niveaus = list(
            self.sessie.execute(
                select(CompetenceLevel.name).where(CompetenceLevel.profile_id == profiel.id)
            ).scalars()
        )
        if graaf.competentieniveau not in niveaus:
            raise OnbekendeLookupwaarde(
                f"competentieniveau '{graaf.competentieniveau}' bestaat niet in profiel "
                f"'{profiel.name}' versie {profiel.version}. Bekende niveaus: "
                + (", ".join(sorted(niveaus)) or "(geen)")
                + ". Een oordeel berekenen voor een niveau dat het profiel niet kent, zou een "
                "oordeel zijn over iets ongedefinieerds."
            )
        qawaid_geladen = list(
            self.sessie.execute(
                select(ProfileQaida.qaida_id).where(ProfileQaida.profile_id == profiel.id)
            ).scalars()
        )

        cykels = steunkringen(graaf)  # eigenschap van de ontleding, stap 1
        analyses = self._vormanalyses(graaf)  # stap 2
        verzwegen = self._verzwegen_premissen(graaf, analyses)
        self._vul_kritische_vragen(graaf, analyses, profiel)  # stap 6
        drogredenen = self._drogredenen(graaf, analyses, cykels)  # stap 7
        rekening = bereken(graaf, self.schaal, analyses, cykels=cykels)  # stap 10

        metadata = {
            "profiel_naam": profiel.name,
            "profiel_versie": profiel.version,
            "qawaid_geladen": bool(qawaid_geladen),
            "burden_allocation": profiel.burden_allocation,
            "versies": {
                "motor": MOTOR_VERSIE,
                "contract": CONTRACT_VERSIE,
                "invoerschema": INVOERSCHEMA_VERSIE,
                "profiel": profiel.version,
                "regelset": regelset_versie(self.sessie),
            },
            "voorbehouden": list(VOORBEHOUDEN_FASE1),
            "interim_regels": [regel.als_dict() for regel in INTERIM_REGELS],
            "drogredenscan": DROGREDENSCAN_FASE1,
        }

        beoordelingen = []
        for claim_ref in graaf.volgorde_claims:
            punten = kantelmodule.zoek(graaf, self.schaal, analyses, claim_ref)  # stap 11
            beoordelingen.append(
                bouw_beoordeling(  # stap 12
                    graaf=graaf,
                    berekening=rekening,
                    schaal=self.schaal,
                    vormanalyses=analyses,
                    claim_ref=claim_ref,
                    drogredenen=drogredenen,
                    verzwegen=verzwegen,
                    kantelpunten=punten,
                    kernregels=self.kernregels,
                    metadata=metadata,
                )
            )

        uitvoer = {
            "voortgebracht_door": "motor zonder taalmodel",
            "versies": metadata["versies"],
            "ontleding": {
                "inzending": graaf.kop,
                "claims": [
                    {"ref": ref, "tekst": graaf.claims[ref].tekst} for ref in graaf.volgorde_claims
                ],
                "premissen": [
                    {
                        "ref": ref,
                        "tekst": graaf.premissen[ref].tekst,
                        "ouder": graaf.premissen[ref].ouder_ref,
                        "type": graaf.premissen[ref].type,
                        "herkomst": graaf.premissen[ref].provenance.kind,
                    }
                    for ref in graaf.volgorde_premissen
                ],
                "inferenties": [
                    {
                        "ref": ref,
                        "van": list(inferentie.van),
                        "naar": inferentie.naar,
                        "schema": inferentie.scheme,
                    }
                    for ref, inferentie in graaf.inferenties.items()
                ],
            },
            "beoordelingen": beoordelingen,
        }
        verifieer(uitvoer)

        if opslaan:
            self._sla_op(invoer, graaf, rekening, uitvoer, profiel, actor, metadata)
        return uitvoer

    # ------------------------------------------------------------------
    # Opslag
    # ------------------------------------------------------------------

    def _weiger_niet_gebouwde_gebruiksvorm(self, gebruiksvorm: str) -> None:
        """Weiger een gebruiksvorm die deze fase nog niet uitvoert.

        Vanaf welke fase een vorm wordt uitgevoerd, staat als data in de lookup
        (§1 geeft de fasetoewijzing). De motor kent alleen haar eigen fase. Een
        beoordeling teruggeven onder een vlag die niet is uitgevoerd, zou een
        onware bewering over de eigen uitvoer zijn.
        """
        klasse = LOOKUP_KLASSEN["use_form"]
        rij = self.sessie.get(klasse, gebruiksvorm)
        vanaf = rij.rangorde if rij is not None else None
        if vanaf is None or vanaf > GEBOUWDE_FASE:
            uitvoerbaar = sorted(
                sleutel
                for sleutel, fase in self.sessie.execute(select(klasse.key, klasse.rangorde)).all()
                if fase is not None and fase <= GEBOUWDE_FASE
            )
            reden = (
                "die vorm hoort niet bij dit bouwplan"
                if vanaf is None
                else f"die vorm wordt pas vanaf fase {vanaf} uitgevoerd"
            )
            raise InvoerFout(
                f"gebruiksvorm '{gebruiksvorm}' bestaat in het schema, maar {reden}. "
                f"Deze motor bouwt fase {GEBOUWDE_FASE} en voert uit: "
                + (", ".join(uitvoerbaar) or "(geen)")
                + "."
            )

    def _weiger_niet_verwerkte_velden(self, graaf: Graaf) -> None:
        """Weiger invoer die fase 1 zou aannemen en vervolgens laten vallen.

        Stil weggooien is erger dan weigeren: de indiener denkt dan dat zijn
        gegeven is meegewogen.
        """
        met_interpretatie = [
            ref
            for ref, inferentie in graaf.inferenties.items()
            if inferentie.interpretation_ref is not None
        ]
        if met_interpretatie:
            raise InvoerFout(
                "deze inferenties verwijzen naar een interpretatie: "
                + ", ".join(sorted(met_interpretatie))
                + ". De interpretatielaag draait pas in fase 4; de motor zou de verwijzing nu "
                "aannemen en laten vallen, en dat zou de indruk wekken dat zij is meegewogen."
            )
        met_corpus = [
            ref
            for ref, premisse in graaf.premissen.items()
            if premisse.provenance.retrieval_ref is not None
        ]
        if met_corpus:
            raise InvoerFout(
                "deze premissen verwijzen naar een zoeksessie in het corpus: "
                + ", ".join(sorted(met_corpus))
                + ". Het corpus is in deze fase leeg en wordt niet geraadpleegd; de verwijzing "
                "zou zonder betekenis worden opgeslagen."
            )

    def _sla_op(
        self,
        invoer: InzendingInvoer,
        graaf: Graaf,
        rekening: Berekening,
        uitvoer: dict[str, Any],
        profiel: Profile,
        actor: str,
        metadata: dict[str, Any],
    ) -> None:
        sessie = self.sessie
        inzending = Submission(
            external_ref=invoer.submission.id,
            title=invoer.submission.title,
            language=invoer.submission.language,
            invoerschema_versie=invoer.schema_version,
            ruwe_invoer=invoer.model_dump(mode="json", by_alias=True),
            created_by=actor,
        )
        sessie.add(inzending)
        sessie.flush()

        claim_rijen: dict[str, ClaimRij] = {}
        for ref in graaf.volgorde_claims:
            claim = graaf.claims[ref]
            rij = ClaimRij(
                submission_id=inzending.id,
                external_ref=ref,
                text=claim.tekst,
                form=claim.vorm,
                termen=list(claim.termen),
            )
            sessie.add(rij)
            claim_rijen[ref] = rij
        sessie.flush()

        premisse_rijen: dict[str, PremiseRij] = {}
        for positie, ref in enumerate(graaf.volgorde_premissen):
            premisse = graaf.premissen[ref]
            rij = PremiseRij(
                submission_id=inzending.id,
                external_ref=ref,
                text=premisse.tekst,
                type=premisse.type,
                explicit=premisse.explicit,
                positie=positie,
                thubut_id=self._score_rij(premisse.thubut),
                dalalah_id=self._score_rij(premisse.dalalah),
                status_label=premisse.status.label if premisse.status else None,
                status_opposition=premisse.status.opposition if premisse.status else None,
                citation_source_ref=premisse.citation.source_ref,
                citation_verification_status=premisse.citation.verification_status,
                proposed_by=premisse.proposed_by,
                confirmed=premisse.confirmed,
                provenance=premisse.provenance.kind,
                provenance_detail=premisse.provenance.detail,
                instrument_output=premisse.instrument_output,
                form=premisse.vorm,
                termen=list(premisse.termen),
                asserts_claim_id=(
                    claim_rijen[premisse.asserts_claim].id if premisse.asserts_claim else None
                ),
            )
            sessie.add(rij)
            premisse_rijen[ref] = rij
        sessie.flush()
        for ref, rij in premisse_rijen.items():
            ouder = graaf.premissen[ref].ouder_ref
            if ouder:
                rij.parent_premise_id = premisse_rijen[ouder].id
        sessie.flush()

        for ref, inferentie in graaf.inferenties.items():
            rij = InferenceRij(
                submission_id=inzending.id,
                external_ref=ref,
                to_claim_id=claim_rijen[inferentie.naar].id,
                scheme=inferentie.scheme,
                strength_id=self._score_rij(inferentie.aangeleverde_sterkte),
                proposed_by=inferentie.proposed_by,
                confirmed=inferentie.confirmed,
            )
            sessie.add(rij)
            sessie.flush()
            for positie, premisse_ref in enumerate(inferentie.van):
                sessie.add(
                    InferencePremise(
                        inference_id=rij.id,
                        premise_id=premisse_rijen[premisse_ref].id,
                        positie=positie,
                    )
                )
            for positie, vraag in enumerate(inferentie.kritische_vragen):
                sessie.add(
                    InferenceCriticalQuestion(
                        inference_id=rij.id,
                        question=vraag.vraag,
                        status=vraag.status,
                        effect=vraag.effect,
                        toelichting=vraag.toelichting,
                        beantwoord_door_motor=vraag.beantwoord_door_motor,
                        positie=positie,
                    )
                )
        sessie.flush()

        for beoordeling in uitvoer["beoordelingen"]:
            claim_ref = beoordeling["claim_ref"]
            kracht = ScoreRij(
                label=beoordeling["probative_force"]["label"],
                rationale=beoordeling["probative_force"]["rationale"],
                computed_by="engine_kernel",
                version=MOTOR_VERSIE,
            )
            sessie.add(kracht)
            sessie.flush()

            vorige = self._vorige_beoordeling(invoer.submission.id, claim_ref)
            rij = Assessment(
                claim_id=claim_rijen[claim_ref].id,
                claim_ref=claim_ref,
                submission_id=inzending.id,
                profile_id=profiel.id,
                profile_version=profiel.version,
                competence_level=graaf.competentieniveau,
                engine_version=MOTOR_VERSIE,
                ruleset_version=metadata["versies"]["regelset"],
                contract_version=CONTRACT_VERSIE,
                use_form=graaf.gebruiksvorm,
                probative_force_id=kracht.id,
                falsifiability_exposure=beoordeling["falsifiability_exposure"],
                weakest_element=beoordeling["weakest_element"],
                insufficient_evidence=beoordeling["insufficient_evidence"]["waarde"],
                insufficient_evidence_explanation=beoordeling["insufficient_evidence"]["uitleg"],
                supersedes=vorige.id if vorige else None,
                rapport=beoordeling,
                created_by=actor,
            )
            sessie.add(rij)
            sessie.flush()

            for vraag in beoordeling["open_critical_questions"]:
                sessie.add(
                    AssessmentOpenQuestion(
                        assessment_id=rij.id,
                        inference_ref=vraag["inferentie_ref"],
                        question=vraag["vraag"],
                        status=vraag["status"],
                        effect=vraag["effect"],
                    )
                )
            for drogreden in beoordeling["fallacies"]:
                sessie.add(
                    AssessmentFallacy(
                        assessment_id=rij.id,
                        fallacy_type=drogreden["soort"],
                        element_kind=drogreden["element_soort"],
                        element_ref=drogreden["element_ref"],
                        rationale=drogreden["rationale"],
                        kernregel=drogreden["kernregel"],
                    )
                )
            for punt in beoordeling["tipping_points"]:
                sessie.add(
                    AssessmentTippingPoint(
                        assessment_id=rij.id,
                        element_kind=punt["element_soort"],
                        element_ref=punt["element_ref"],
                        veld=punt["veld"],
                        current_label=punt["current_label"],
                        change_needed=punt["change_needed"],
                        would_flip_to=punt["would_flip_to"],
                        direction=punt["richting"],
                    )
                )
            for voorstel in beoordeling["possible_unstated_premises"]:
                sessie.add(
                    AssessmentUnstatedPremise(
                        assessment_id=rij.id,
                        inference_ref=voorstel["inferentie_ref"],
                        voorstel=voorstel["voorstel"],
                        basis=voorstel["basis"],
                        rationale=voorstel["rationale"],
                        proposed_by=voorstel["voorgesteld_door"],
                        confirmed=voorstel["bevestigd"],
                    )
                )
            for kernregel in beoordeling["kernel_rules_applied"]:
                sessie.add(
                    AssessmentDependency(
                        assessment_id=rij.id,
                        dependency_kind="kernel_rule",
                        dependency_id=kernregel["key"],
                        dependency_version=self.kernregels[kernregel["key"]]["version"],
                        toelichting="kernregel die een bevinding in deze beoordeling draagt",
                    )
                )
            sessie.add(
                AssessmentDependency(
                    assessment_id=rij.id,
                    dependency_kind="profile",
                    dependency_id=profiel.name,
                    dependency_version=profiel.version,
                    toelichting="profiel waaronder deze beoordeling is berekend",
                )
            )
            for premisse_ref in sorted(
                {
                    ref
                    for lijn in beoordeling["chain"]["bewijslijnen"]
                    for ref in _premisse_refs(lijn["premissen"])
                }
            ):
                sessie.add(
                    AssessmentDependency(
                        assessment_id=rij.id,
                        dependency_kind="premise",
                        dependency_id=premisse_ref,
                        dependency_version=invoer.schema_version,
                        toelichting="premisse in de keten van deze beoordeling",
                    )
                )
            schrijf_audit(
                sessie,
                entity_kind="assessment",
                entity_id=rij.id,
                action="create",
                actor=actor,
                reden=f"beoordeling van claim '{claim_ref}' onder profiel '{profiel.name}'",
                erna={"label": beoordeling["probative_force"]["label"]},
            )
        sessie.flush()

    def _score_rij(self, score: Any) -> str | None:
        if score is None:
            return None
        rij = ScoreRij(
            label=score.label,
            rationale=score.rationale,
            computed_by=score.computed_by,
            version=score.version,
            instrument_ref=score.instrument,
        )
        self.sessie.add(rij)
        self.sessie.flush()
        return rij.id

    def _vorige_beoordeling(self, inzending_ref: str | None, claim_ref: str) -> Assessment | None:
        """De kop van de keten voor dezelfde claim in dezelfde inzending.

        Zonder externe verwijzing op de inzending is er geen identiteit over
        runs heen en wordt niets opgevolgd.
        """
        if not inzending_ref:
            return None
        kandidaten = list(
            self.sessie.execute(
                select(Assessment)
                .join(Submission, Assessment.submission_id == Submission.id)
                .where(Submission.external_ref == inzending_ref)
                .where(Assessment.claim_ref == claim_ref)
            ).scalars()
        )
        if not kandidaten:
            return None
        opgevolgd = {k.supersedes for k in kandidaten if k.supersedes}
        koppen = [k for k in kandidaten if k.id not in opgevolgd]
        return koppen[0] if koppen else None


def _ontdubbel(bevindingen: list[DrogredenBevinding]) -> list[DrogredenBevinding]:
    """Eén bevinding per (soort, element). Dubbel tellen is verboden."""
    gezien: set[tuple[str, str, str]] = set()
    uniek: list[DrogredenBevinding] = []
    for bevinding in bevindingen:
        sleutel = (bevinding.soort, bevinding.element_soort, bevinding.element_ref)
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        uniek.append(bevinding)
    return uniek


def _premisse_refs(knopen: list[dict[str, Any]]) -> list[str]:
    """Elke premisse in de keten, ook die achter een claimgrens.

    De afhankelijkheden van een beoordeling moeten net zo ver reiken als haar
    keten. Stoppen bij de claimgrens zou betekenen dat een wijziging in een
    premisse die de zwakste schakel is, niet als afhankelijkheid zichtbaar is.
    """
    gevonden: list[str] = []
    for knoop in knopen:
        gevonden.append(knoop["ref"])
        gevonden.extend(_premisse_refs(knoop["sub_premissen"]))
        onderliggend = knoop.get("keten_van_beweerde_claim")
        if onderliggend:
            for lijn in onderliggend["bewijslijnen"]:
                gevonden.extend(_premisse_refs(lijn["premissen"]))
    return gevonden


def profielinstelling(profiel: Profile, veld: str) -> Any:
    """Lees een profielinstelling die bepaald moet zijn.

    Is de instelling niet bepaald, dan faalt de bewerking met een melding. Er
    wordt niet teruggevallen op een standaardwaarde, want elke standaardwaarde
    is al een standpunt.
    """
    waarde = getattr(profiel, veld, None)
    if waarde is None:
        raise OnbepaaldeProfielinstelling(
            f"profiel '{profiel.name}' versie {profiel.version} laat '{veld}' onbepaald. "
            "Deze bewerking hangt ervan af en valt niet terug op een standaardwaarde: "
            "elke standaardwaarde zou al een standpunt zijn. Stel het veld in het profiel in."
        )
    return waarde
