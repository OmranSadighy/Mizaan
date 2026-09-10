"""Datamodel per bouwspecificatie §5.

Uitgangspunten die het schema afdwingen:

* Geen enum voor een inhoudelijk veld (§2.9). Elk gesloten ogend vocabulaire is
  een lookup-tabel ``lu_<vocabulaire>`` met een tekstsleutel, en elk veld dat
  ernaar wijst is een vreemde sleutel. Wie een waarde wil toevoegen, voegt een
  rij toe; er hoeft geen code te veranderen.
* Eén generieke relatietabel (§2.10). ``edge`` draagt ``relation_type``; er is
  geen aparte kolom of tabel per relatiesoort.
* Elke score is een record met een verplichte ``rationale`` (§5, inleiding).
  Een lege rationale wordt door een CHECK-constraint geweigerd.
* Alles versioneerd (§2.8).
* Nooit één getal (§2.5). Sterkte is een verwijzing naar een label, niet een
  numerieke kolom. De enige numerieke kolommen in dit schema zijn ordeningen
  (``rangorde``, ``positie``) die de motor nooit als uitvoer teruggeeft.

Alle tabellen uit §5 worden aangemaakt, ook de tabellen die pas in een latere
fase gevuld worden.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import JSON

# --------------------------------------------------------------------------
# Vocabulaires. Deze lijst bepaalt welke lookup-tabellen bestaan; de inhoud van
# elke tabel komt uit seed/lookups.json en staat niet in code.
# --------------------------------------------------------------------------

VOCABULAIRES: tuple[str, ...] = (
    "strength_label",
    "premise_type",
    "scheme",
    "relation_type",
    "node_kind",
    "qaida_function",
    "derivation_method",
    "qaida_status",
    "verification_status",
    "proposed_by",
    "provenance_kind",
    "score_source",
    "critical_question_status",
    "critical_question_effect",
    "critical_question_origin",
    "ground_kind",
    "burden_allocation",
    "scope_relation",
    "use_form",
    "form_kind",
    "categorical_quantity",
    "form_status",
    "fallacy_type",
    "unstated_premise_basis",
    "tipping_direction",
    "audit_action",
)


def nieuw_id() -> str:
    return uuid.uuid4().hex


def nu() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class _LookupKolommen:
    """Kolommen die elke lookup-tabel deelt."""

    key = Column(String, primary_key=True)
    label_nl = Column(Text, nullable=False)
    label_en = Column(Text, nullable=False)
    omschrijving = Column(Text, nullable=True)
    # Ordening, uitsluitend intern. Verlaat de motor nooit als uitvoer.
    rangorde = Column(Integer, nullable=True)
    # Optionele verwijzing naar de kernregel die deze soort bevinding draagt.
    kernregel = Column(String, ForeignKey("kernel_rule.key"), nullable=True)
    actief = Column(Boolean, nullable=False, default=True)
    bron = Column(Text, nullable=True)


def _klassenaam(vocabulaire: str) -> str:
    return "Lu" + "".join(deel.capitalize() for deel in vocabulaire.split("_"))


LOOKUP_KLASSEN: dict[str, type] = {}
for _vocabulaire in VOCABULAIRES:
    LOOKUP_KLASSEN[_vocabulaire] = type(
        _klassenaam(_vocabulaire),
        (Base, _LookupKolommen),
        {"__tablename__": f"lu_{_vocabulaire}", "__doc__": f"Lookup voor {_vocabulaire}."},
    )


def _fk(vocabulaire: str) -> ForeignKey:
    return ForeignKey(f"lu_{vocabulaire}.key")


# --------------------------------------------------------------------------
# §5.1 kernel_rule
# --------------------------------------------------------------------------


class KernelRule(Base):
    """Kernregel (§5.1). Onveranderlijk; beschermd door databasetriggers."""

    __tablename__ = "kernel_rule"

    key = Column(String, primary_key=True)
    statement_nl = Column(Text, nullable=False)
    statement_en = Column(Text, nullable=False)
    self_refutation_argument = Column(Text, nullable=False)
    immutable = Column(Boolean, nullable=False, default=True)
    version = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=nu)

    __table_args__ = (
        CheckConstraint("length(trim(self_refutation_argument)) > 0", name="ck_kernregel_bewijs"),
        # Onveranderlijk is geen instelling maar de definitie van een kernregel.
        # Zonder deze constraint zou een rij met immutable = 0 langs de triggers
        # glippen die de kern beschermen.
        CheckConstraint("immutable = 1", name="ck_kernregel_onveranderlijk"),
    )


# --------------------------------------------------------------------------
# Score (§5 inleiding): {label, rationale, computed_by, version}
# --------------------------------------------------------------------------


class Score(Base):
    __tablename__ = "score"

    id = Column(String, primary_key=True, default=nieuw_id)
    label = Column(String, _fk("strength_label"), nullable=False)
    rationale = Column(Text, nullable=False)
    computed_by = Column(String, _fk("score_source"), nullable=False)
    version = Column(String, nullable=False)
    # Welk instrument de score leverde; leeg bij handmatige invoer. Houdt
    # handmatige scores onderscheidbaar van instrumentuitvoer (fase 3).
    instrument_ref = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=nu)

    __table_args__ = (CheckConstraint("length(trim(rationale)) > 0", name="ck_score_rationale"),)


# --------------------------------------------------------------------------
# §5.2 profile
# --------------------------------------------------------------------------


class Profile(Base):
    __tablename__ = "profile"

    id = Column(String, primary_key=True, default=nieuw_id)
    name = Column(Text, nullable=False)
    version = Column(String, nullable=False)
    type_set_exhaustive = Column(Boolean, nullable=False, default=False)
    # Bewust nullable: elke booleaanse waarde is al een standpunt. Een bewerking
    # die van dit veld afhangt terwijl het null is, faalt met een melding.
    figurative_reading_permitted = Column(Boolean, nullable=True)
    conflict_order = Column(JSON, nullable=False, default=list)
    burden_allocation = Column(String, _fk("burden_allocation"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=nu)

    __table_args__ = (UniqueConstraint("name", "version", name="uq_profiel_naam_versie"),)


class ProfilePremiseType(Base):
    """Welke premissetypen in een profiel bestaan, met hun plafond (§5.2)."""

    __tablename__ = "profile_premise_type"

    id = Column(String, primary_key=True, default=nieuw_id)
    profile_id = Column(String, ForeignKey("profile.id"), nullable=False)
    premise_type = Column(String, _fk("premise_type"), nullable=False)
    # Plafond mag leeg zijn in het schema; de laadvalidatie die een leeg plafond
    # tot laadfout maakt hoort bij fase 2.
    ceiling_label = Column(String, _fk("strength_label"), nullable=True)

    __table_args__ = (UniqueConstraint("profile_id", "premise_type", name="uq_profiel_type"),)


class ProfileQaida(Base):
    __tablename__ = "profile_qaida"

    id = Column(String, primary_key=True, default=nieuw_id)
    profile_id = Column(String, ForeignKey("profile.id"), nullable=False)
    qaida_id = Column(String, ForeignKey("qaida.id"), nullable=False)

    __table_args__ = (UniqueConstraint("profile_id", "qaida_id", name="uq_profiel_qaida"),)


class CompetenceLevel(Base):
    __tablename__ = "competence_level"

    id = Column(String, primary_key=True, default=nieuw_id)
    profile_id = Column(String, ForeignKey("profile.id"), nullable=False)
    name = Column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("profile_id", "name", name="uq_profiel_niveau"),)


class CompetenceLevelQaida(Base):
    __tablename__ = "competence_level_qaida"

    id = Column(String, primary_key=True, default=nieuw_id)
    competence_level_id = Column(String, ForeignKey("competence_level.id"), nullable=False)
    qaida_id = Column(String, ForeignKey("qaida.id"), nullable=False)


# --------------------------------------------------------------------------
# §5.3 qaida
# --------------------------------------------------------------------------


class Qaida(Base):
    __tablename__ = "qaida"

    id = Column(String, primary_key=True, default=nieuw_id)
    key = Column(String, nullable=False, unique=True)
    statement_ar = Column(Text, nullable=True)
    statement_nl = Column(Text, nullable=False)
    statement_en = Column(Text, nullable=True)
    function = Column(String, _fk("qaida_function"), nullable=False)
    # Verplicht per §5.3: op welke gevallen de regel van toepassing is.
    scope = Column(Text, nullable=False)
    own_strength_id = Column(String, ForeignKey("score.id"), nullable=True)
    effective_strength_id = Column(String, ForeignKey("score.id"), nullable=True)
    derivation_method = Column(String, _fk("derivation_method"), nullable=False)
    status = Column(String, _fk("qaida_status"), nullable=False)
    domain = Column(Text, nullable=True)
    version = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=nu)

    __table_args__ = (CheckConstraint("length(trim(scope)) > 0", name="ck_qaida_scope"),)


class QaidaEvidence(Base):
    """Het eigen bewijs van een qaida (§5.3), recursief via premissen."""

    __tablename__ = "qaida_evidence"

    id = Column(String, primary_key=True, default=nieuw_id)
    qaida_id = Column(String, ForeignKey("qaida.id"), nullable=False)
    premise_id = Column(String, ForeignKey("premise.id"), nullable=False)
    positie = Column(Integer, nullable=False, default=0)


class QaidaStatusHistory(Base):
    """Register van statuswijzigingen van een qaida (§5.12)."""

    __tablename__ = "qaida_status_history"

    id = Column(String, primary_key=True, default=nieuw_id)
    qaida_id = Column(String, ForeignKey("qaida.id"), nullable=False)
    oude_status = Column(String, _fk("qaida_status"), nullable=True)
    nieuwe_status = Column(String, _fk("qaida_status"), nullable=False)
    reden = Column(Text, nullable=False)
    actor = Column(Text, nullable=False)
    regelset_versie = Column(String, nullable=True)
    # §5.12: welke beoordeling de aanleiding was, indien er een was.
    triggering_assessment_ref = Column(String, ForeignKey("assessment.id"), nullable=True)
    gewijzigd_op = Column(DateTime, nullable=False, default=nu)


# --------------------------------------------------------------------------
# §5.4 edge: de ene generieke relatietabel
# --------------------------------------------------------------------------


class Edge(Base):
    __tablename__ = "edge"

    id = Column(String, primary_key=True, default=nieuw_id)
    from_id = Column(String, nullable=False)
    from_kind = Column(String, _fk("node_kind"), nullable=False)
    to_id = Column(String, nullable=False)
    to_kind = Column(String, _fk("node_kind"), nullable=False)
    relation_type = Column(String, _fk("relation_type"), nullable=False)
    toelichting = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=nu)


# --------------------------------------------------------------------------
# Inzending, claims, premissen, inferenties
# --------------------------------------------------------------------------


class Submission(Base):
    __tablename__ = "submission"

    id = Column(String, primary_key=True, default=nieuw_id)
    external_ref = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    invoerschema_versie = Column(String, nullable=False)
    ruwe_invoer = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=nu)
    created_by = Column(Text, nullable=False)


class Claim(Base):
    __tablename__ = "claim"

    id = Column(String, primary_key=True, default=nieuw_id)
    submission_id = Column(String, ForeignKey("submission.id"), nullable=False)
    external_ref = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    form = Column(JSON, nullable=True)
    termen = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("submission_id", "external_ref", name="uq_claim_ref"),
        CheckConstraint("length(trim(text)) > 0", name="ck_claim_tekst"),
    )


class Premise(Base):
    """§5.6. ``provenance`` is verplicht."""

    __tablename__ = "premise"

    id = Column(String, primary_key=True, default=nieuw_id)
    submission_id = Column(String, ForeignKey("submission.id"), nullable=True)
    external_ref = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    type = Column(String, _fk("premise_type"), nullable=True)
    explicit = Column(Boolean, nullable=False, default=True)
    parent_premise_id = Column(String, ForeignKey("premise.id"), nullable=True)
    positie = Column(Integer, nullable=False, default=0)

    thubut_id = Column(String, ForeignKey("score.id"), nullable=True)
    dalalah_id = Column(String, ForeignKey("score.id"), nullable=True)

    # Statuslabel draagt altijd de tegenstelling waarin het gebruikt wordt.
    status_label = Column(Text, nullable=True)
    status_opposition = Column(Text, nullable=True)

    citation_source_ref = Column(Text, nullable=True)
    citation_verification_status = Column(String, _fk("verification_status"), nullable=True)

    instrument_output = Column(JSON, nullable=True)
    proposed_by = Column(String, _fk("proposed_by"), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)

    # Verplichte herkomst (§5.6).
    provenance = Column(String, _fk("provenance_kind"), nullable=False)
    provenance_detail = Column(JSON, nullable=True)
    # Alleen gevuld bij provenance = engine_retrieved (§5.6).
    retrieval_ref = Column(String, ForeignKey("retrieval_session.id"), nullable=True)

    form = Column(JSON, nullable=True)
    termen = Column(JSON, nullable=True)
    # Welke claim deze premisse beweert; maakt ketens over claims heen mogelijk.
    asserts_claim_id = Column(String, ForeignKey("claim.id"), nullable=True)

    __table_args__ = (
        CheckConstraint("length(trim(text)) > 0", name="ck_premisse_tekst"),
        # Een statuslabel draagt altijd de tegenstelling waarin het gebruikt
        # wordt (§5.6): muhkam tegenover mutashabih is iets anders dan muhkam
        # tegenover mansukh. Een label zonder tegenstelling is betekenisloos en
        # wordt daarom op schemaniveau geweigerd.
        # De IS NOT NULL-toetsen staan er met opzet: zonder hen levert de
        # vergelijking NULL op in plaats van onwaar, en een CHECK die NULL
        # oplevert laat de rij door.
        CheckConstraint(
            "(status_label IS NULL AND status_opposition IS NULL) OR ("
            "status_label IS NOT NULL AND status_opposition IS NOT NULL "
            "AND length(trim(status_label)) > 0 AND length(trim(status_opposition)) > 0)",
            name="ck_premisse_status_tegenstelling",
        ),
    )


class Interpretation(Base):
    """§5.7. Gevuld vanaf fase 4."""

    __tablename__ = "interpretation"

    id = Column(String, primary_key=True, default=nieuw_id)
    submission_id = Column(String, ForeignKey("submission.id"), nullable=True)
    external_ref = Column(Text, nullable=True)
    text_ref = Column(Text, nullable=False)
    proposed_meaning = Column(Text, nullable=False)
    strength_id = Column(String, ForeignKey("score.id"), nullable=True)


class InterpretationGround(Base):
    __tablename__ = "interpretation_ground"

    id = Column(String, primary_key=True, default=nieuw_id)
    interpretation_id = Column(String, ForeignKey("interpretation.id"), nullable=False)
    kind = Column(String, _fk("ground_kind"), nullable=False)
    text = Column(Text, nullable=False)
    score_id = Column(String, ForeignKey("score.id"), nullable=True)


class InterpretationSupporter(Base):
    """Wie de lezing aanhing. Telt niet mee in de score; dient als ta'yid."""

    __tablename__ = "interpretation_supporter"

    id = Column(String, primary_key=True, default=nieuw_id)
    interpretation_id = Column(String, ForeignKey("interpretation.id"), nullable=False)
    name = Column(Text, nullable=False)
    toelichting = Column(Text, nullable=True)


class Inference(Base):
    """§5.8."""

    __tablename__ = "inference"

    id = Column(String, primary_key=True, default=nieuw_id)
    submission_id = Column(String, ForeignKey("submission.id"), nullable=False)
    external_ref = Column(Text, nullable=False)
    to_claim_id = Column(String, ForeignKey("claim.id"), nullable=False)
    scheme = Column(String, _fk("scheme"), nullable=True)
    # Verplicht bij een tekstpremisse vanaf fase 4; in fase 1 vastgelegd, niet
    # afgedwongen, omdat de dalalah-stap nog niet draait.
    interpretation_id = Column(String, ForeignKey("interpretation.id"), nullable=True)
    strength_id = Column(String, ForeignKey("score.id"), nullable=True)
    proposed_by = Column(String, _fk("proposed_by"), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)

    __table_args__ = (UniqueConstraint("submission_id", "external_ref", name="uq_inferentie_ref"),)


class InferencePremise(Base):
    __tablename__ = "inference_premise"

    id = Column(String, primary_key=True, default=nieuw_id)
    inference_id = Column(String, ForeignKey("inference.id"), nullable=False)
    premise_id = Column(String, ForeignKey("premise.id"), nullable=False)
    positie = Column(Integer, nullable=False, default=0)


class SchemeCriticalQuestion(Base):
    """Sjabloon van een kritische vraag bij een schema (§5.8).

    Een profiel kan de vragenset van een schema uitbreiden: zo'n rij krijgt
    ``origin = profile`` en verwijst naar de qaida die haar toevoegt.
    """

    __tablename__ = "scheme_critical_question"

    id = Column(String, primary_key=True, default=nieuw_id)
    scheme = Column(String, _fk("scheme"), nullable=False)
    volgnummer = Column(Text, nullable=False)
    vraag_nl = Column(Text, nullable=False)
    vraag_en = Column(Text, nullable=True)
    standaard_effect = Column(String, _fk("critical_question_effect"), nullable=False)
    origin = Column(String, _fk("critical_question_origin"), nullable=False)
    # §5.8: waaraan de vraag ontleend is. Bij een basisvraag een
    # literatuurverwijzing (bv. walton_2008), bij een profielvraag een
    # verwijzing naar de qaida die haar toevoegt; die staat daarnaast als
    # vreemde sleutel in added_by_qaida_id, zodat de verwijzing integer blijft.
    source_ref = Column(Text, nullable=True)
    added_by_qaida_id = Column(String, ForeignKey("qaida.id"), nullable=True)
    profile_id = Column(String, ForeignKey("profile.id"), nullable=True)
    # Naam van een motorcapaciteit die deze vraag zelf kan beantwoorden.
    beantwoordbaar_door_motor = Column(Text, nullable=True)
    version = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("scheme", "volgnummer", "profile_id", name="uq_schema_vraag"),
    )


class InferenceCriticalQuestion(Base):
    """Instantie van een kritische vraag bij één inferentie (§5.8)."""

    __tablename__ = "inference_critical_question"

    id = Column(String, primary_key=True, default=nieuw_id)
    inference_id = Column(String, ForeignKey("inference.id"), nullable=False)
    template_id = Column(String, ForeignKey("scheme_critical_question.id"), nullable=True)
    question = Column(Text, nullable=False)
    status = Column(String, _fk("critical_question_status"), nullable=False)
    effect = Column(String, _fk("critical_question_effect"), nullable=False)
    toelichting = Column(Text, nullable=True)
    beantwoord_door_motor = Column(Boolean, nullable=False, default=False)
    positie = Column(Integer, nullable=False, default=0)


# --------------------------------------------------------------------------
# §5.9 assessment, append-only register (§5.12)
# --------------------------------------------------------------------------


class Assessment(Base):
    """§5.9. Append-only: wijzigen en verwijderen wordt door triggers geweigerd.

    Een herziene beoordeling is een nieuwe rij die via ``supersedes`` naar haar
    voorganger wijst.
    """

    __tablename__ = "assessment"

    id = Column(String, primary_key=True, default=nieuw_id)
    claim_id = Column(String, ForeignKey("claim.id"), nullable=False)
    claim_ref = Column(Text, nullable=False)
    submission_id = Column(String, ForeignKey("submission.id"), nullable=False)

    profile_id = Column(String, ForeignKey("profile.id"), nullable=False)
    profile_version = Column(String, nullable=False)
    competence_level = Column(Text, nullable=False)
    engine_version = Column(String, nullable=False)
    ruleset_version = Column(String, nullable=False)
    contract_version = Column(String, nullable=False)
    use_form = Column(String, _fk("use_form"), nullable=False)

    probative_force_id = Column(String, ForeignKey("score.id"), nullable=False)
    # Aparte as naast sterkte: hoeveel de claim uitsluit. Geen getal.
    falsifiability_exposure = Column(JSON, nullable=False)

    weakest_element = Column(JSON, nullable=True)
    insufficient_evidence = Column(Boolean, nullable=False, default=False)
    insufficient_evidence_explanation = Column(Text, nullable=True)

    supersedes = Column(String, ForeignKey("assessment.id"), nullable=True)
    # §5.12: een beoordeling met een verouderde afhankelijkheid krijgt stale = true
    # en wordt nooit stilzwijgend herrekend. superseded_by staat er niet als
    # kolom bij: die zou het terugschrijven op een append-only rij vereisen en
    # is af te leiden uit supersedes. Zie docs/verschillen-met-de-spec.md.
    stale = Column(Boolean, nullable=False, default=False)
    rapport = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=nu)
    created_by = Column(Text, nullable=False)


class AssessmentDialecticalForce(Base):
    """Dialectische kracht tegenover één opgegeven profiel (§5.9).

    Op aanvraag berekend, niet vooraf tegen alle profielen (§4.3).
    """

    __tablename__ = "assessment_dialectical_force"

    id = Column(String, primary_key=True, default=nieuw_id)
    assessment_id = Column(String, ForeignKey("assessment.id"), nullable=False)
    against_profile_id = Column(String, ForeignKey("profile.id"), nullable=False)
    score_id = Column(String, ForeignKey("score.id"), nullable=False)


class AssessmentOpenQuestion(Base):
    __tablename__ = "assessment_open_question"

    id = Column(String, primary_key=True, default=nieuw_id)
    assessment_id = Column(String, ForeignKey("assessment.id"), nullable=False)
    inference_ref = Column(Text, nullable=False)
    question = Column(Text, nullable=False)
    status = Column(String, _fk("critical_question_status"), nullable=False)
    effect = Column(String, _fk("critical_question_effect"), nullable=False)


class AssessmentFallacy(Base):
    __tablename__ = "assessment_fallacy"

    id = Column(String, primary_key=True, default=nieuw_id)
    assessment_id = Column(String, ForeignKey("assessment.id"), nullable=False)
    fallacy_type = Column(String, _fk("fallacy_type"), nullable=False)
    element_kind = Column(String, _fk("node_kind"), nullable=False)
    element_ref = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    kernregel = Column(String, ForeignKey("kernel_rule.key"), nullable=False)


class AssessmentTippingPoint(Base):
    __tablename__ = "assessment_tipping_point"

    id = Column(String, primary_key=True, default=nieuw_id)
    assessment_id = Column(String, ForeignKey("assessment.id"), nullable=False)
    element_kind = Column(String, _fk("node_kind"), nullable=False)
    element_ref = Column(Text, nullable=False)
    veld = Column(Text, nullable=False)
    current_label = Column(Text, nullable=False)
    change_needed = Column(Text, nullable=False)
    would_flip_to = Column(Text, nullable=False)
    direction = Column(String, _fk("tipping_direction"), nullable=False)


class AssessmentDependency(Base):
    """Waarvan een beoordeling afhing (§5.12).

    Maakt achteraf zichtbaar welke beoordelingen meebewegen als een qaida,
    kernregel of premisse verandert.
    """

    __tablename__ = "assessment_dependency"

    id = Column(String, primary_key=True, default=nieuw_id)
    assessment_id = Column(String, ForeignKey("assessment.id"), nullable=False)
    dependency_kind = Column(String, _fk("node_kind"), nullable=False)
    dependency_id = Column(Text, nullable=False)
    dependency_version = Column(String, nullable=True)
    toelichting = Column(Text, nullable=True)


class AssessmentUnstatedPremise(Base):
    """Mogelijk verzwegen premissen die de motor voorstelde (§6 stap 2)."""

    __tablename__ = "assessment_unstated_premise"

    id = Column(String, primary_key=True, default=nieuw_id)
    assessment_id = Column(String, ForeignKey("assessment.id"), nullable=False)
    inference_ref = Column(Text, nullable=False)
    voorstel = Column(Text, nullable=False)
    basis = Column(String, _fk("unstated_premise_basis"), nullable=False)
    rationale = Column(Text, nullable=False)
    proposed_by = Column(String, _fk("proposed_by"), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)


# --------------------------------------------------------------------------
# §5.10 comparison. Aangemaakt, gevuld vanaf fase 6.
# --------------------------------------------------------------------------


class Comparison(Base):
    __tablename__ = "comparison"

    id = Column(String, primary_key=True, default=nieuw_id)
    profile_id = Column(String, ForeignKey("profile.id"), nullable=False)
    profile_version = Column(String, nullable=False)
    engine_version = Column(String, nullable=True)
    ruleset_version = Column(String, nullable=True)
    contract_version = Column(String, nullable=True)
    scope_relation = Column(String, _fk("scope_relation"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=nu)


class ComparisonClaim(Base):
    __tablename__ = "comparison_claim"

    id = Column(String, primary_key=True, default=nieuw_id)
    comparison_id = Column(String, ForeignKey("comparison.id"), nullable=False)
    claim_id = Column(String, ForeignKey("claim.id"), nullable=False)
    zijde = Column(Text, nullable=True)


class ComparisonSharedPremise(Base):
    __tablename__ = "comparison_shared_premise"

    id = Column(String, primary_key=True, default=nieuw_id)
    comparison_id = Column(String, ForeignKey("comparison.id"), nullable=False)
    premise_id = Column(String, ForeignKey("premise.id"), nullable=False)


class ComparisonDivergencePoint(Base):
    __tablename__ = "comparison_divergence_point"

    id = Column(String, primary_key=True, default=nieuw_id)
    comparison_id = Column(String, ForeignKey("comparison.id"), nullable=False)
    proposition = Column(Text, nullable=False)
    side_a_grounds = Column(JSON, nullable=True)
    side_b_grounds = Column(JSON, nullable=True)
    testable_on_text = Column(Boolean, nullable=False, default=False)
    deciding_question = Column(Text, nullable=True)


# --------------------------------------------------------------------------
# §5.11 audit_log
# --------------------------------------------------------------------------


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=nieuw_id)
    entity_kind = Column(String, _fk("node_kind"), nullable=False)
    entity_id = Column(Text, nullable=False)
    action = Column(String, _fk("audit_action"), nullable=False)
    actor = Column(Text, nullable=False)
    reden = Column(Text, nullable=False)
    ervoor = Column(JSON, nullable=True)
    erna = Column(JSON, nullable=True)
    op = Column(DateTime, nullable=False, default=nu)

    __table_args__ = (CheckConstraint("length(trim(reden)) > 0", name="ck_audit_reden"),)


# --------------------------------------------------------------------------
# §5.13 corpus. Aangemaakt en leeg; fase 1 schrijft er geen code voor.
# De gebruiksvormen aanvallen en verdedigen halen hier later bewijs uit.
# --------------------------------------------------------------------------


class CorpusSource(Base):
    """§5.13. Een brontekst of verzameling."""

    __tablename__ = "corpus_source"

    id = Column(String, primary_key=True, default=nieuw_id)
    name = Column(Text, nullable=False)
    kind = Column(Text, nullable=True)
    license = Column(Text, nullable=True)
    access_method = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=nu)


class CorpusEntry(Base):
    """§5.13. Een adresseerbare eenheid binnen een bron: vers, hadith, passage."""

    __tablename__ = "corpus_entry"

    id = Column(String, primary_key=True, default=nieuw_id)
    source_ref = Column(String, ForeignKey("corpus_source.id"), nullable=False)
    locator = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    language = Column(Text, nullable=True)


class RetrievalSession(Base):
    """§5.13. Eén zoektocht in het corpus, met wat er niet is gevonden.

    Hiermee verschilt "geen sterke aanval gevonden" aantoonbaar van "niet
    gezocht", zoals §4.4 eist. ``mode`` verwijst naar de gebruiksvorm; alleen
    aanvallen en verdedigen halen premissen op.
    """

    __tablename__ = "retrieval_session"

    id = Column(String, primary_key=True, default=nieuw_id)
    mode = Column(String, _fk("use_form"), nullable=False)
    claim_ref = Column(String, ForeignKey("claim.id"), nullable=True)
    query = Column(Text, nullable=False)
    executed_at = Column(DateTime, nullable=False, default=nu)
    not_found_note = Column(Text, nullable=True)


class RetrievalSessionScope(Base):
    """``corpus_scope[]`` van een zoeksessie (§5.13).

    Een aparte tabel in plaats van een lijst in één kolom, zodat de verwijzing
    naar de doorzochte bron een echte vreemde sleutel is.
    """

    __tablename__ = "retrieval_session_scope"

    id = Column(String, primary_key=True, default=nieuw_id)
    retrieval_session_id = Column(String, ForeignKey("retrieval_session.id"), nullable=False)
    corpus_source_id = Column(String, ForeignKey("corpus_source.id"), nullable=False)


class RetrievalSessionFound(Base):
    """``found[]`` van een zoeksessie (§5.13), om dezelfde reden een eigen tabel."""

    __tablename__ = "retrieval_session_found"

    id = Column(String, primary_key=True, default=nieuw_id)
    retrieval_session_id = Column(String, ForeignKey("retrieval_session.id"), nullable=False)
    corpus_entry_id = Column(String, ForeignKey("corpus_entry.id"), nullable=False)
    positie = Column(Integer, nullable=False, default=0)


CORPUS_TABELLEN: tuple[str, ...] = (
    "corpus_source",
    "corpus_entry",
    "retrieval_session",
    "retrieval_session_scope",
    "retrieval_session_found",
)
