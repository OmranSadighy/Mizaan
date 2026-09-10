"""Schema aanmaken, seed laden, register bijhouden."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..configuratie import STANDAARD_SEED, Configuratie
from ..fouten import InvoerFout, OnbekendeLookupwaarde
from . import overzichten, triggers
from .model import (
    LOOKUP_KLASSEN,
    AuditLog,
    Base,
    CompetenceLevel,
    KernelRule,
    Profile,
    ProfilePremiseType,
    Qaida,
    SchemeCriticalQuestion,
)


def standaard_seed_map() -> Path:
    """De seed-map uit de omgeving; geen pad staat hardgecodeerd (§11)."""
    return Configuratie.uit_omgeving().controleer_seed()


# Bewaard als naam voor bestaande aanroepers; de waarde komt uit de omgeving.
SEED_MAP = Configuratie(databasepad="", seed_map=STANDAARD_SEED, uitvoer_map=Path()).seed_map


def maak_engine(url: str = "sqlite+pysqlite:///:memory:") -> Engine:
    engine = create_engine(url, future=True)

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record):  # pragma: no cover - triviale hook
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def maak_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as verbinding:
        triggers.installeer(verbinding)
        overzichten.installeer(verbinding)


def maak_sessiefabriek(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def open_sessie(engine: Engine) -> Iterator[Session]:
    fabriek = maak_sessiefabriek(engine)
    sessie = fabriek()
    try:
        yield sessie
        sessie.commit()
    except Exception:
        sessie.rollback()
        raise
    finally:
        sessie.close()


# --------------------------------------------------------------------------
# Seed
# --------------------------------------------------------------------------


def _lees(pad: Path) -> Any:
    return json.loads(pad.read_text(encoding="utf-8"))


def laad_seed(sessie: Session, seed_map: Path | None = None, actor: str = "seed") -> dict[str, int]:
    """Laad kernregels, lookups, kritische vragen en profielen.

    De volgorde is bindend: kernregels eerst, omdat lookup-rijen naar de
    kernregel kunnen verwijzen die hun soort bevinding draagt.

    Zonder opgegeven map komt de seed-map uit de omgeving (§11).
    """
    if seed_map is None:
        seed_map = standaard_seed_map()
    telling: dict[str, int] = {}

    kern = _lees(seed_map / "kernel_rules.json")
    for regel in kern["regels"]:
        sessie.add(
            KernelRule(
                key=regel["key"],
                statement_nl=regel["statement_nl"],
                statement_en=regel["statement_en"],
                self_refutation_argument=regel["self_refutation_argument"],
                immutable=True,
                version=kern["versie"],
            )
        )
    sessie.flush()
    telling["kernel_rule"] = len(kern["regels"])

    lookups = _lees(seed_map / "lookups.json")
    aantal = 0
    for vocabulaire, blok in lookups["vocabulaires"].items():
        klasse = LOOKUP_KLASSEN.get(vocabulaire)
        if klasse is None:
            raise OnbekendeLookupwaarde(
                f"seed bevat vocabulaire '{vocabulaire}' dat het schema niet kent"
            )
        for rij in blok["rijen"]:
            sessie.add(
                klasse(
                    key=rij["key"],
                    label_nl=rij["label_nl"],
                    label_en=rij["label_en"],
                    omschrijving=rij.get("omschrijving"),
                    rangorde=rij.get("rangorde"),
                    kernregel=rij.get("kernregel"),
                    actief=rij.get("actief", True),
                    bron=f"seed/lookups.json@{lookups['versie']}",
                )
            )
            aantal += 1
    sessie.flush()
    telling["lookup"] = aantal

    vragen = _lees(seed_map / "critical_questions.json")
    for vraag in vragen["vragen"]:
        sessie.add(
            SchemeCriticalQuestion(
                scheme=vraag["scheme"],
                volgnummer=vraag["volgnummer"],
                vraag_nl=vraag["vraag_nl"],
                vraag_en=vraag.get("vraag_en"),
                standaard_effect=vraag["standaard_effect"],
                origin="base",
                herkomst_bron=vraag.get("herkomst_bron", vragen.get("herkomst_bron")),
                beantwoordbaar_door_motor=vraag.get("beantwoordbaar_door_motor"),
                version=vragen["versie"],
            )
        )
    sessie.flush()
    telling["scheme_critical_question"] = len(vragen["vragen"])

    profielen = sorted((seed_map / "profielen").glob("*.json"))
    for pad in profielen:
        laad_profiel(sessie, _lees(pad))
    telling["profile"] = len(profielen)

    sessie.flush()
    for soort, aantal_rijen in telling.items():
        schrijf_audit(
            sessie,
            entity_kind=_node_kind_voor(soort),
            entity_id=soort,
            action="seed",
            actor=actor,
            reden=f"seed geladen uit {seed_map}",
            erna={"aantal_rijen": str(aantal_rijen)},
        )
    sessie.flush()
    return telling


def _node_kind_voor(soort: str) -> str:
    return {
        "kernel_rule": "kernel_rule",
        "lookup": "taxonomy_entry",
        "scheme_critical_question": "critical_question",
        "profile": "profile",
    }[soort]


def laad_profiel(sessie: Session, data: dict[str, Any]) -> Profile:
    """Sla een profielrecord op.

    De validatie dat elk premissetype een bepaald plafond heeft, hoort bij
    fase 2 en gebeurt hier bewust niet.
    """
    gevraagde_qawaid = list(data.get("qaida_set") or []) + [
        sleutel
        for niveau in (data.get("competence_levels") or [])
        for sleutel in (niveau.get("qaida_set") or [])
    ]
    if gevraagde_qawaid:
        raise InvoerFout(
            f"profiel '{data.get('name')}' noemt qawa'id: "
            + ", ".join(sorted(set(gevraagde_qawaid)))
            + ". De regellaag wordt in fase 2 gebouwd. De motor laadt ze nu niet en zou ze "
            "stilzwijgend negeren, waardoor het profiel iets anders zou doen dan het zegt."
        )
    profiel = Profile(
        name=data["name"],
        version=data["version"],
        type_set_exhaustive=bool(data.get("type_set_exhaustive", False)),
        figurative_reading_permitted=data.get("figurative_reading_permitted"),
        conflict_order=data.get("conflict_order", []),
        burden_allocation=_verplicht(data, "burden_allocation"),
    )
    sessie.add(profiel)
    sessie.flush()

    plafonds = data.get("type_ceilings", {}) or {}
    for premissetype in data.get("type_set", []) or []:
        sessie.add(
            ProfilePremiseType(
                profile_id=profiel.id,
                premise_type=premissetype,
                ceiling_label=plafonds.get(premissetype),
            )
        )
    for niveau in data.get("competence_levels", []) or []:
        sessie.add(CompetenceLevel(profile_id=profiel.id, name=niveau["name"]))
    sessie.flush()
    return profiel


def _verplicht(data: dict[str, Any], veld: str) -> Any:
    """Lees een profielveld dat het profiel zelf moet noemen.

    B1 noemt een standaardwaarde voor de bewijslast. Die standaard hoort in het
    profielrecord te staan, niet in de laadcode: anders zou een profiel dat er
    niets over zegt stilzwijgend een standpunt innemen dat nergens is vastgelegd.
    """
    waarde = data.get(veld)
    if waarde is None:
        raise InvoerFout(
            f"profiel '{data.get('name')}' noemt '{veld}' niet. Dit veld stuurt het oordeel en "
            "hoort in het profielrecord te staan; de laadcode kiest er geen waarde bij."
        )
    return waarde


def haal_profiel(sessie: Session, naam: str, versie: str | None = None) -> Profile:
    vraag = select(Profile).where(Profile.name == naam)
    if versie is not None:
        vraag = vraag.where(Profile.version == versie)
    profiel = sessie.execute(vraag.order_by(Profile.version.desc())).scalars().first()
    if profiel is None:
        raise OnbekendeLookupwaarde(f"profiel '{naam}' bestaat niet")
    return profiel


# --------------------------------------------------------------------------
# Register
# --------------------------------------------------------------------------


def regelset_versie(sessie: Session) -> str:
    """Vingerafdruk van alle data die het oordeel stuurt.

    Een tekstuele hash, geen getal. Zij dekt de kernregels, de qawa'id, de
    lookup-rijen voor zover die het rekenen sturen, en de sjablonen van de
    kritische vragen. Dat moet zo: omdat regels data zijn, verandert het oordeel
    mee met een gewijzigde rij, en een vingerafdruk die zo'n wijziging niet ziet
    maakt een beoordeling onreproduceerbaar (randvoorwaarde 2.8).

    Alleen de sturende velden tellen mee. Een gewijzigde Nederlandse vertaling
    van een label verandert het oordeel niet en de vingerafdruk dus ook niet.
    """
    kern = sessie.execute(select(KernelRule).order_by(KernelRule.key)).scalars().all()
    qawaid = sessie.execute(select(Qaida).order_by(Qaida.key)).scalars().all()

    vocabulaires: dict[str, list[dict[str, Any]]] = {}
    for naam, klasse in sorted(LOOKUP_KLASSEN.items()):
        rijen = sessie.execute(select(klasse).order_by(klasse.key)).scalars().all()
        vocabulaires[naam] = [
            {
                "key": rij.key,
                "rangorde": rij.rangorde,
                "kernregel": rij.kernregel,
                "actief": bool(rij.actief),
            }
            for rij in rijen
        ]

    vragen = (
        sessie.execute(
            select(SchemeCriticalQuestion).order_by(
                SchemeCriticalQuestion.scheme, SchemeCriticalQuestion.volgnummer
            )
        )
        .scalars()
        .all()
    )

    ruggengraat = {
        "kernel_rules": [
            {"key": r.key, "version": r.version, "statement_nl": r.statement_nl} for r in kern
        ],
        "qawaid": [
            {"key": q.key, "version": q.version, "status": q.status, "function": q.function}
            for q in qawaid
        ],
        "vocabulaires": vocabulaires,
        "critical_questions": [
            {
                "scheme": v.scheme,
                "volgnummer": v.volgnummer,
                "origin": v.origin,
                "profile_id": v.profile_id,
                "added_by_qaida_id": v.added_by_qaida_id,
                "standaard_effect": v.standaard_effect,
                "beantwoordbaar_door_motor": v.beantwoordbaar_door_motor,
                "version": v.version,
            }
            for v in vragen
        ],
    }
    ruw = json.dumps(ruggengraat, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(ruw).hexdigest()[:32]


def schrijf_audit(
    sessie: Session,
    *,
    entity_kind: str,
    entity_id: str,
    action: str,
    actor: str,
    reden: str,
    ervoor: dict[str, Any] | None = None,
    erna: dict[str, Any] | None = None,
) -> AuditLog:
    regel = AuditLog(
        entity_kind=entity_kind,
        entity_id=entity_id,
        action=action,
        actor=actor,
        reden=reden,
        ervoor=ervoor,
        erna=erna,
    )
    sessie.add(regel)
    return regel


def wijzig_qaida_status(
    sessie: Session, qaida: Qaida, nieuwe_status: str, *, actor: str, reden: str
) -> None:
    """Wijzig de status van een qaida en leg dat in het register vast.

    De historieregel wordt door een databasetrigger geschreven; deze functie
    draagt actor en reden aan die trigger over en schrijft daarnaast de
    auditregel.
    """
    oude_status = qaida.status
    triggers.zet_context(
        sessie.connection(), actor=actor, reden=reden, regelset_versie=regelset_versie(sessie)
    )
    qaida.status = nieuwe_status
    sessie.flush()
    schrijf_audit(
        sessie,
        entity_kind="qaida",
        entity_id=qaida.key,
        action="status_change",
        actor=actor,
        reden=reden,
        ervoor={"status": oude_status},
        erna={"status": nieuwe_status},
    )
    sessie.flush()
