"""Afgeleide overzichten uit §5.12.

Vier vragen die het register moet kunnen beantwoorden, plus de keten van
opvolgende beoordelingen. Ze staan als views en niet als tabel, omdat ze niets
toevoegen aan wat er al is opgeslagen; ze zeggen alleen hoe je ernaar kijkt.

Over ``superseded_by``: §5.12 noemt het naast ``supersedes``. Het staat hier als
view en niet als kolom, want een kolom zou betekenen dat de motor terugschrijft
op een rij die append-only is. Dezelfde paragraaf eist juist dat een beoordeling
nooit wordt overschreven. De verwijzing vooruit is exact af te leiden uit de
verwijzing terug, dus er gaat geen informatie verloren. Zie
``docs/verschillen-met-de-spec.md``.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

VIEW_SQL: tuple[str, ...] = (
    # De keten van beoordelingen, met de verwijzing vooruit erbij.
    """
    CREATE VIEW IF NOT EXISTS v_beoordeling_keten AS
    SELECT
        a.id                AS assessment_id,
        a.claim_ref         AS claim_ref,
        a.profile_id        AS profile_id,
        a.profile_version   AS profile_version,
        a.supersedes        AS supersedes,
        opvolger.id         AS superseded_by,
        a.stale             AS stale,
        a.created_at        AS created_at
    FROM assessment a
    LEFT JOIN assessment opvolger ON opvolger.supersedes = a.id;
    """,
    # Regels die de toets hebben doorstaan en actief zijn.
    """
    CREATE VIEW IF NOT EXISTS v_qawaid_doorstaan AS
    SELECT q.id, q.key, q.statement_nl, q.function, q.scope, q.version, q.status
    FROM qaida q
    WHERE q.status = 'active';
    """,
    # Regels die zijn afgevallen, met reden en aanleiding.
    """
    CREATE VIEW IF NOT EXISTS v_qawaid_afgevallen AS
    SELECT
        q.id                            AS qaida_id,
        q.key                           AS qaida_key,
        q.status                        AS huidige_status,
        h.oude_status                   AS van_status,
        h.nieuwe_status                 AS naar_status,
        h.reden                         AS reden,
        h.actor                         AS gewijzigd_door,
        h.gewijzigd_op                  AS gewijzigd_op,
        h.triggering_assessment_ref     AS aanleiding_beoordeling
    FROM qaida q
    JOIN qaida_status_history h ON h.qaida_id = q.id
    WHERE q.status IN ('rejected', 'defeated', 'conflicts_with_kernel');
    """,
    # Regels die op elkaar steunen, via de ene generieke relatietabel.
    """
    CREATE VIEW IF NOT EXISTS v_qaida_steunrelaties AS
    SELECT
        e.relation_type AS relatie,
        bron.key        AS van_qaida,
        doel.key        AS naar_qaida,
        e.toelichting   AS toelichting
    FROM edge e
    JOIN qaida bron ON bron.id = e.from_id AND e.from_kind = 'qaida'
    JOIN qaida doel ON doel.id = e.to_id  AND e.to_kind  = 'qaida';
    """,
    # Beoordelingen die verouderd zijn: expliciet gemarkeerd, of met een
    # afhankelijkheid waarvan de versie inmiddels is veranderd.
    """
    CREATE VIEW IF NOT EXISTS v_verouderde_beoordelingen AS
    SELECT DISTINCT
        a.id                            AS assessment_id,
        a.claim_ref                     AS claim_ref,
        d.dependency_kind               AS afhankelijkheid_soort,
        d.dependency_id                 AS afhankelijkheid_ref,
        d.dependency_version            AS vastgelegde_versie,
        CASE d.dependency_kind
            WHEN 'kernel_rule' THEN
                (SELECT k.version FROM kernel_rule k WHERE k.key = d.dependency_id)
            WHEN 'qaida' THEN
                (SELECT q.version FROM qaida q WHERE q.key = d.dependency_id)
            WHEN 'profile' THEN
                (SELECT p.version FROM profile p WHERE p.name = d.dependency_id)
        END                             AS huidige_versie,
        a.stale                         AS gemarkeerd_stale
    FROM assessment a
    JOIN assessment_dependency d ON d.assessment_id = a.id
    WHERE a.stale = 1
       OR (
            d.dependency_kind IN ('kernel_rule', 'qaida', 'profile')
            AND d.dependency_version IS NOT NULL
            AND d.dependency_version <> COALESCE(
                CASE d.dependency_kind
                    WHEN 'kernel_rule' THEN
                (SELECT k.version FROM kernel_rule k WHERE k.key = d.dependency_id)
                    WHEN 'qaida' THEN
                (SELECT q.version FROM qaida q WHERE q.key = d.dependency_id)
                    WHEN 'profile' THEN
                (SELECT p.version FROM profile p WHERE p.name = d.dependency_id)
                END,
                d.dependency_version
            )
       );
    """,
)

OVERZICHTEN: tuple[str, ...] = (
    "v_beoordeling_keten",
    "v_qawaid_doorstaan",
    "v_qawaid_afgevallen",
    "v_qaida_steunrelaties",
    "v_verouderde_beoordelingen",
)


def installeer(verbinding: Connection) -> None:
    """Maak de afgeleide overzichten aan. Idempotent."""
    for ddl in VIEW_SQL:
        verbinding.execute(text(ddl))
