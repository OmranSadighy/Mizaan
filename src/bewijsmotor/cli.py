"""Minimale invoer via bestand. Nog geen webinterface, nog geen taalmodel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import MOTOR_VERSIE
from .contract import weiger_enkel_getal
from .db.registry import laad_seed, maak_engine, maak_schema, open_sessie
from .fouten import MotorFout
from .motor.engine import Motor


def _engine_voor(db: str):
    url = "sqlite+pysqlite:///:memory:" if db == ":memory:" else f"sqlite+pysqlite:///{db}"
    return maak_engine(url)


def _init(argumenten: argparse.Namespace) -> int:
    engine = _engine_voor(argumenten.db)
    maak_schema(engine)
    with open_sessie(engine) as sessie:
        telling = laad_seed(sessie, actor=argumenten.actor)
    print(f"schema aangemaakt in {argumenten.db}")
    for soort, aantal in telling.items():
        print(f"  {soort}: {aantal} rijen")
    return 0


def _beoordeel(argumenten: argparse.Namespace) -> int:
    if argumenten.enkel_getal:
        weiger_enkel_getal("verzoek om één samenvattend cijfer")

    engine = _engine_voor(argumenten.db)
    maak_schema(engine)
    ruw = json.loads(Path(argumenten.bestand).read_text(encoding="utf-8"))
    with open_sessie(engine) as sessie:
        if argumenten.seed:
            laad_seed(sessie, actor=argumenten.actor)
        motor = Motor(sessie)
        uitvoer = motor.beoordeel(ruw, actor=argumenten.actor, opslaan=not argumenten.droog)

    tekst = json.dumps(uitvoer, ensure_ascii=False, indent=2)
    if argumenten.uit:
        Path(argumenten.uit).write_text(tekst, encoding="utf-8")
        print(f"beoordeling geschreven naar {argumenten.uit}")
    else:
        print(tekst)
    return 0


def main(argv: list[str] | None = None) -> int:
    ontleder = argparse.ArgumentParser(
        prog="bewijsmotor",
        description=(
            "Beoordeelt de kwaliteit van bewijsvoering achter claims. "
            "Beoordeelt geen waarheid en geen personen."
        ),
    )
    ontleder.add_argument("--versie", action="version", version=MOTOR_VERSIE)
    subs = ontleder.add_subparsers(dest="opdracht", required=True)

    init = subs.add_parser("init", help="schema aanmaken en seed laden")
    init.add_argument("--db", default="bewijsmotor.sqlite3")
    init.add_argument("--actor", default="cli")
    init.set_defaults(func=_init)

    beoordeel = subs.add_parser("beoordeel", help="een gestructureerd JSON-bestand beoordelen")
    beoordeel.add_argument("bestand")
    beoordeel.add_argument("--db", default=":memory:")
    beoordeel.add_argument("--actor", default="cli")
    beoordeel.add_argument("--uit", default=None, help="schrijf de uitvoer naar dit bestand")
    beoordeel.add_argument(
        "--seed", action="store_true", default=True, help="laad de seed voor het beoordelen"
    )
    beoordeel.add_argument("--geen-seed", dest="seed", action="store_false")
    beoordeel.add_argument(
        "--droog", action="store_true", help="niet opslaan, alleen berekenen en tonen"
    )
    beoordeel.add_argument(
        "--enkel-getal",
        action="store_true",
        help="vraag om één samenvattend cijfer (wordt geweigerd, met uitleg)",
    )
    beoordeel.set_defaults(func=_beoordeel)

    argumenten = ontleder.parse_args(argv)
    try:
        return int(argumenten.func(argumenten))
    except MotorFout as fout:
        print(f"{type(fout).__name__}: {fout}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
