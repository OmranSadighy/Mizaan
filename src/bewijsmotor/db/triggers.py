"""Databasetriggers die de onveranderlijkheid en het register afdwingen.

Drie garanties, op databaseniveau zodat ook een rechtstreekse schrijfactie ze
niet omzeilt:

1. Kernregels (§2.3, §5.1) zijn niet te wijzigen en niet te verwijderen.
2. Beoordelingen (§5.12) zijn append-only. Een herziening is een nieuwe rij die
   via ``supersedes`` naar haar voorganger wijst.
3. Elke statuswijziging van een qaida (§5.12) belandt in
   ``qaida_status_history``, ook wanneer de aanroeper dat vergeet.

``register_context`` draagt actor, reden en regelsetversie de trigger in. De
helper in ``registry.py`` vult haar; blijft zij leeg, dan legt de trigger dat
zichtbaar vast in plaats van de wijziging stil door te laten.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

REGISTER_CONTEXT_DDL = """
CREATE TABLE IF NOT EXISTS register_context (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    actor TEXT,
    reden TEXT,
    regelset_versie TEXT
);
"""

TRIGGER_SQL: tuple[str, ...] = (
    """
    CREATE TRIGGER IF NOT EXISTS trg_kernregel_geen_update
    BEFORE UPDATE ON kernel_rule
    FOR EACH ROW WHEN OLD.immutable = 1
    BEGIN
        SELECT RAISE(ABORT,
            'kernregel is onveranderlijk: wijzigen geweigerd (bouwspecificatie 2.3)');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_kernregel_geen_delete
    BEFORE DELETE ON kernel_rule
    FOR EACH ROW WHEN OLD.immutable = 1
    BEGIN
        SELECT RAISE(ABORT,
            'kernregel is onveranderlijk: verwijderen geweigerd (bouwspecificatie 2.3)');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_beoordeling_append_only_update
    BEFORE UPDATE ON assessment
    FOR EACH ROW
    BEGIN
        SELECT RAISE(ABORT,
            'beoordeling is append-only: wijzig niet, voeg een nieuwe rij toe met supersedes');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_beoordeling_append_only_delete
    BEFORE DELETE ON assessment
    FOR EACH ROW
    BEGIN
        SELECT RAISE(ABORT,
            'beoordeling is append-only: verwijderen geweigerd');
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_qaida_statushistorie
    AFTER UPDATE OF status ON qaida
    FOR EACH ROW WHEN OLD.status IS NOT NEW.status
    BEGIN
        INSERT INTO qaida_status_history
            (id, qaida_id, oude_status, nieuwe_status, reden, actor,
             regelset_versie, gewijzigd_op)
        VALUES (
            lower(hex(randomblob(16))),
            NEW.id,
            OLD.status,
            NEW.status,
            COALESCE((SELECT reden FROM register_context WHERE id = 1),
                     'geen reden vastgelegd bij de wijziging'),
            COALESCE((SELECT actor FROM register_context WHERE id = 1), 'onbekend'),
            (SELECT regelset_versie FROM register_context WHERE id = 1),
            CURRENT_TIMESTAMP
        );
    END;
    """,
)


def installeer(verbinding: Connection) -> None:
    """Maak de contexttabel en alle triggers aan. Idempotent."""
    verbinding.execute(text(REGISTER_CONTEXT_DDL))
    for ddl in TRIGGER_SQL:
        verbinding.execute(text(ddl))


def zet_context(
    verbinding: Connection, actor: str, reden: str, regelset_versie: str | None = None
) -> None:
    """Leg actor en reden vast voor de triggers in deze transactie."""
    verbinding.execute(
        text(
            "INSERT INTO register_context (id, actor, reden, regelset_versie) "
            "VALUES (1, :actor, :reden, :versie) "
            "ON CONFLICT(id) DO UPDATE SET actor = :actor, reden = :reden, "
            "regelset_versie = :versie"
        ),
        {"actor": actor, "reden": reden, "versie": regelset_versie},
    )
