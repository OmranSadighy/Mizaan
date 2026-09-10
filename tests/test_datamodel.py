"""Het datamodel uit §5 en de eisen die het schema zelf moet afdwingen."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from bewijsmotor.db.model import (
    CORPUS_TABELLEN,
    LOOKUP_KLASSEN,
    VOCABULAIRES,
    Assessment,
    AssessmentDependency,
    AuditLog,
    Base,
    Edge,
    KernelRule,
    Premise,
    Qaida,
    QaidaStatusHistory,
    Score,
)
from bewijsmotor.db.registry import regelset_versie, wijzig_qaida_status
from bewijsmotor.motor.engine import Motor
from conftest import lees_voorbeeld

BRON = Path(__file__).resolve().parents[1] / "src" / "bewijsmotor"

TABELLEN_UIT_PARAGRAAF_5 = {
    "kernel_rule",
    "profile",
    "qaida",
    "edge",
    "premise",
    "interpretation",
    "inference",
    "assessment",
    "comparison",
    "audit_log",
    "qaida_status_history",
    "assessment_dependency",
}


def test_alle_tabellen_uit_paragraaf_5_bestaan():
    aanwezig = set(Base.metadata.tables)
    ontbreekt = TABELLEN_UIT_PARAGRAAF_5 - aanwezig
    assert not ontbreekt, f"ontbrekende tabellen: {sorted(ontbreekt)}"


def test_geen_enum_voor_inhoudelijke_velden():
    """Randvoorwaarde §2.9: lookup-tabellen, geen enums."""
    for tabelnaam, tabel in Base.metadata.tables.items():
        for kolom in tabel.columns:
            assert not isinstance(kolom.type, sa.Enum), (
                f"{tabelnaam}.{kolom.name} gebruikt een enum in plaats van een lookup-tabel"
            )


def test_geen_gesloten_lijst_in_de_python_code():
    """Ook in de code staat geen gesloten opsomming voor een inhoudelijk veld."""
    verdacht = re.compile(r"\bLiteral\[|\(str,\s*Enum\)|\benum\.Enum\b|\(Enum\)")
    for pad in BRON.rglob("*.py"):
        tekst = pad.read_text(encoding="utf-8")
        treffers = verdacht.findall(tekst)
        assert not treffers, f"{pad.name} bevat een gesloten opsomming: {treffers}"


def test_elk_vocabulaire_heeft_een_gevulde_lookup_tabel(sessie):
    for vocabulaire in VOCABULAIRES:
        klasse = LOOKUP_KLASSEN[vocabulaire]
        aantal = sessie.execute(select(func.count()).select_from(klasse)).scalar_one()
        assert aantal > 0, f"lookup '{vocabulaire}' is leeg"


def test_een_generieke_relatietabel(sessie):
    """Randvoorwaarde §2.10: relaties zijn rijen met een relation_type."""
    kolommen = {kolom.name for kolom in Edge.__table__.columns}
    assert {"from_id", "from_kind", "to_id", "to_kind", "relation_type"} <= kolommen
    relatiesoorten = set(sessie.execute(select(LOOKUP_KLASSEN["relation_type"].key)).scalars())
    assert {"depends_on", "attacks", "supports"} <= relatiesoorten
    # Er is geen tweede tabel die één relatiesoort apart modelleert.
    verdacht = [
        naam
        for naam in Base.metadata.tables
        if naam.endswith(("_attacks", "_supports", "_depends_on"))
    ]
    assert verdacht == []


def test_kernregels_zijn_aanwezig_en_onveranderlijk(sessie):
    regels = sessie.execute(select(KernelRule)).scalars().all()
    assert 4 <= len(regels) <= 5, "§5.1 vraagt vier tot vijf kernregels"
    for regel in regels:
        assert regel.immutable is True
        assert regel.self_refutation_argument.strip()

    with pytest.raises(IntegrityError, match="onveranderlijk"):
        sessie.execute(
            text("UPDATE kernel_rule SET statement_nl = 'x' WHERE key = :k"), {"k": regels[0].key}
        )
    sessie.rollback()

    with pytest.raises(IntegrityError, match="onveranderlijk"):
        sessie.execute(text("DELETE FROM kernel_rule WHERE key = :k"), {"k": regels[0].key})
    sessie.rollback()


def test_score_zonder_rationale_wordt_geweigerd(sessie):
    sessie.add(Score(label="weak", rationale="   ", computed_by="manual_input", version="0.1.0"))
    with pytest.raises(IntegrityError):
        sessie.flush()
    sessie.rollback()


def test_premisse_zonder_herkomst_wordt_geweigerd(sessie):
    sessie.add(
        Premise(
            external_ref="p_zonder_herkomst",
            text="tekst",
            proposed_by="user",
        )
    )
    with pytest.raises(IntegrityError):
        sessie.flush()
    sessie.rollback()


def test_beoordeling_is_append_only_en_volgt_op(engine, sessie):
    motor = Motor(sessie)
    invoer = lees_voorbeeld("nultest_zwakste_schakel.json")

    motor.beoordeel(invoer, actor="test")
    sessie.flush()
    eerste = sessie.execute(select(Assessment)).scalars().all()
    assert len(eerste) == 1
    assert eerste[0].supersedes is None
    eerste_id = eerste[0].id

    motor.beoordeel(invoer, actor="test")
    sessie.flush()
    alle = sessie.execute(select(Assessment)).scalars().all()
    assert len(alle) == 2, "een herziening is een nieuwe rij, geen wijziging"
    opvolger = next(a for a in alle if a.supersedes is not None)
    assert opvolger.supersedes == eerste_id
    sessie.commit()

    with pytest.raises(IntegrityError, match="append-only"):
        sessie.execute(
            text("UPDATE assessment SET competence_level = 'x' WHERE id = :i"),
            {"i": eerste_id},
        )
    sessie.rollback()

    with pytest.raises(IntegrityError, match="append-only"):
        sessie.execute(text("DELETE FROM assessment WHERE id = :i"), {"i": eerste_id})
    sessie.rollback()


def test_beoordeling_legt_haar_afhankelijkheden_vast(sessie):
    Motor(sessie).beoordeel(lees_voorbeeld("nultest_zwakste_schakel.json"), actor="test")
    sessie.flush()
    beoordeling = sessie.execute(select(Assessment)).scalars().one()
    afhankelijk = (
        sessie.execute(
            select(AssessmentDependency).where(AssessmentDependency.assessment_id == beoordeling.id)
        )
        .scalars()
        .all()
    )
    soorten = {rij.dependency_kind for rij in afhankelijk}
    assert {"kernel_rule", "profile", "premise"} <= soorten
    for rij in afhankelijk:
        assert rij.dependency_id
    assert beoordeling.ruleset_version.startswith("sha256:")
    assert beoordeling.engine_version
    assert beoordeling.profile_version
    assert beoordeling.contract_version


def test_statuswijziging_van_een_qaida_komt_in_het_register(sessie):
    score = Score(
        label="probable",
        rationale="handmatig ingevoerd voor deze test",
        computed_by="manual_input",
        version="0.1.0",
    )
    sessie.add(score)
    sessie.flush()
    qaida = Qaida(
        key="test_regel",
        statement_nl="Een regel om het register te toetsen.",
        function="prior",
        scope="uitsluitend deze test",
        derivation_method="rational_axiom",
        status="active",
        version="0.1.0",
        own_strength_id=score.id,
    )
    sessie.add(qaida)
    sessie.flush()

    wijzig_qaida_status(sessie, qaida, "contested", actor="omran", reden="tegenbewijs aangetroffen")

    historie = sessie.execute(select(QaidaStatusHistory)).scalars().all()
    assert len(historie) == 1
    assert historie[0].oude_status == "active"
    assert historie[0].nieuwe_status == "contested"
    assert historie[0].actor == "omran"
    assert historie[0].reden == "tegenbewijs aangetroffen"
    # De historieregel draagt de regelsetversie zoals die gold op het moment van
    # de wijziging, dus vóór de nieuwe status meetelde. Na de wijziging is de
    # regelset een andere; dat verschil hoort er te zijn.
    assert historie[0].regelset_versie.startswith("sha256:")
    assert historie[0].regelset_versie != regelset_versie(sessie)

    audit = (
        sessie.execute(select(AuditLog).where(AuditLog.action == "status_change")).scalars().all()
    )
    assert len(audit) == 1
    assert audit[0].actor == "omran"


def test_statuswijziging_buiten_de_helper_om_wordt_ook_vastgelegd(sessie):
    """Het register hangt niet af van de goede wil van de aanroeper."""
    score = Score(label="weak", rationale="test", computed_by="manual_input", version="0.1.0")
    sessie.add(score)
    sessie.flush()
    qaida = Qaida(
        key="stille_regel",
        statement_nl="Regel die stil van status verandert.",
        function="burden",
        scope="uitsluitend deze test",
        derivation_method="nass",
        status="active",
        version="0.1.0",
        own_strength_id=score.id,
    )
    sessie.add(qaida)
    sessie.flush()

    sessie.execute(text("UPDATE qaida SET status = 'rejected' WHERE key = 'stille_regel'"))
    sessie.flush()

    historie = sessie.execute(select(QaidaStatusHistory)).scalars().all()
    assert len(historie) == 1
    assert historie[0].nieuwe_status == "rejected"
    assert "geen reden" in historie[0].reden or historie[0].reden


def test_corpustabellen_bestaan_en_zijn_leeg(sessie):
    """§5.13: aangemaakt en leeg. Fase 1 schrijft er geen code voor."""
    for tabelnaam in CORPUS_TABELLEN:
        assert tabelnaam in Base.metadata.tables
        aantal = sessie.execute(text(f"SELECT COUNT(*) FROM {tabelnaam}")).scalar_one()
        assert aantal == 0


def test_gebruiksvormen_staan_klaar_zonder_migratie(sessie):
    """De vier gebruiksvormen bestaan als data; fase 1 bouwt alleen 'assess'."""
    vormen = set(sessie.execute(select(LOOKUP_KLASSEN["use_form"].key)).scalars())
    assert {"assess", "compare", "attack", "defend"} <= vormen
    assert "use_form" in {kolom.name for kolom in Assessment.__table__.columns}
    assert "provenance" in {kolom.name for kolom in Premise.__table__.columns}
    assert "provenance_corpus_document_id" in {kolom.name for kolom in Premise.__table__.columns}


def test_profiel_kan_de_vragenset_van_een_schema_uitbreiden(sessie):
    """§5.8: basisvragen dragen hun herkomst, profielvragen hun qaida."""
    from bewijsmotor.db.model import SchemeCriticalQuestion

    kolommen = {kolom.name for kolom in SchemeCriticalQuestion.__table__.columns}
    assert {"origin", "added_by_qaida_id", "profile_id"} <= kolommen
    basisvragen = (
        sessie.execute(
            select(SchemeCriticalQuestion).where(SchemeCriticalQuestion.scheme == "analogy")
        )
        .scalars()
        .all()
    )
    assert basisvragen
    assert all(vraag.origin == "base" for vraag in basisvragen)
    assert all(vraag.added_by_qaida_id is None for vraag in basisvragen)


def test_seed_schrijft_een_auditspoor(sessie):
    regels = sessie.execute(select(AuditLog).where(AuditLog.action == "seed")).scalars().all()
    assert regels
    for regel in regels:
        assert regel.actor
        assert regel.reden


def test_statuslabel_zonder_tegenstelling_wordt_geweigerd(sessie):
    """§5.6: het label draagt altijd de tegenstelling waarin het gebruikt wordt."""
    sessie.add(
        Premise(
            external_ref="p_status",
            text="tekst",
            proposed_by="user",
            provenance="submitted_by_user",
            status_label="muhkam",
        )
    )
    with pytest.raises(IntegrityError):
        sessie.flush()
    sessie.rollback()

    sessie.add(
        Premise(
            external_ref="p_status_ok",
            text="tekst",
            proposed_by="user",
            provenance="submitted_by_user",
            status_label="muhkam",
            status_opposition="mutashabih",
        )
    )
    sessie.flush()


def test_regelsetversie_beweegt_mee_met_de_data(sessie):
    """Regels zijn data, dus moet de vingerafdruk elke sturende rij dekken."""
    voor = regelset_versie(sessie)

    sessie.execute(
        LOOKUP_KLASSEN["fallacy_type"]
        .__table__.update()
        .where(LOOKUP_KLASSEN["fallacy_type"].key == "undistributed_middle")
        .values(kernregel="non_contradictie")
    )
    sessie.flush()
    assert regelset_versie(sessie) != voor, (
        "een gewijzigde koppeling tussen bevinding en kernregel stuurt het oordeel "
        "en hoort de vingerafdruk te veranderen"
    )

    na_koppeling = regelset_versie(sessie)
    sessie.execute(
        LOOKUP_KLASSEN["fallacy_type"]
        .__table__.update()
        .where(LOOKUP_KLASSEN["fallacy_type"].key == "undistributed_middle")
        .values(label_nl="middenterm niet verdeeld")
    )
    sessie.flush()
    assert regelset_versie(sessie) == na_koppeling, (
        "een andere vertaling stuurt het oordeel niet en hoort de vingerafdruk niet te raken"
    )
