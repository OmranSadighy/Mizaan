"""Minimale invoer via bestand. Nog geen webinterface, nog geen taalmodel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import MOTOR_VERSIE
from .configuratie import VARIABELE_DB, VARIABELE_SEED, VARIABELE_UITVOER, Configuratie
from .contract import weiger_enkel_getal
from .db.registry import laad_seed, maak_engine, maak_schema, open_sessie
from .fouten import MotorFout
from .motor.engine import Motor


def _configuratie(argumenten: argparse.Namespace) -> Configuratie:
    """De configuratie komt uit de omgeving; argumenten overschrijven haar."""
    basis = Configuratie.uit_omgeving()
    return Configuratie(
        databasepad=argumenten.db or basis.databasepad,
        seed_map=Path(argumenten.seed) if argumenten.seed else basis.seed_map,
        uitvoer_map=Path(argumenten.uitvoer) if argumenten.uitvoer else basis.uitvoer_map,
    )


def _init(argumenten: argparse.Namespace) -> int:
    configuratie = _configuratie(argumenten)
    engine = maak_engine(configuratie.database_url)
    maak_schema(engine)
    with open_sessie(engine) as sessie:
        telling = laad_seed(sessie, configuratie.controleer_seed(), actor=argumenten.actor)
    print(f"schema aangemaakt in {configuratie.databasepad}")
    print(f"seed geladen uit {configuratie.seed_map}")
    for soort, aantal in telling.items():
        print(f"  {soort}: {aantal} rijen")
    return 0


def _beoordeel(argumenten: argparse.Namespace) -> int:
    if argumenten.enkel_getal:
        weiger_enkel_getal("verzoek om één samenvattend cijfer")

    configuratie = _configuratie(argumenten)
    engine = maak_engine(configuratie.database_url)
    maak_schema(engine)
    ruw = json.loads(Path(argumenten.bestand).read_text(encoding="utf-8"))
    with open_sessie(engine) as sessie:
        if argumenten.laad_seed:
            laad_seed(sessie, configuratie.controleer_seed(), actor=argumenten.actor)
        motor = Motor(sessie)
        uitvoer = motor.beoordeel(ruw, actor=argumenten.actor, opslaan=not argumenten.droog)

    tekst = json.dumps(uitvoer, ensure_ascii=False, indent=2)
    if argumenten.uit:
        doel = Path(argumenten.uit)
        if not doel.is_absolute():
            doel = configuratie.klaargezette_uitvoer_map() / doel
        doel.parent.mkdir(parents=True, exist_ok=True)
        doel.write_text(tekst, encoding="utf-8")
        print(f"beoordeling geschreven naar {doel}")
    else:
        print(tekst)
    return 0


def _toon_configuratie(_argumenten: argparse.Namespace) -> int:
    for naam, waarde in Configuratie.uit_omgeving().als_dict().items():
        print(f"{naam}={waarde}")
    return 0


def _voeg_padargumenten_toe(ontleder: argparse.ArgumentParser) -> None:
    """Paden komen uit de omgeving; deze argumenten overschrijven ze per aanroep."""
    ontleder.add_argument(
        "--db", default=None, help=f"pad naar de database (standaard uit {VARIABELE_DB})"
    )
    ontleder.add_argument(
        "--seed", default=None, help=f"map met de seed (standaard uit {VARIABELE_SEED})"
    )
    ontleder.add_argument(
        "--uitvoer", default=None, help=f"map voor de uitvoer (standaard uit {VARIABELE_UITVOER})"
    )


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
    _voeg_padargumenten_toe(init)
    init.add_argument("--actor", default="cli")
    init.set_defaults(func=_init)

    beoordeel = subs.add_parser("beoordeel", help="een gestructureerd JSON-bestand beoordelen")
    beoordeel.add_argument("bestand")
    _voeg_padargumenten_toe(beoordeel)
    beoordeel.add_argument("--actor", default="cli")
    beoordeel.add_argument(
        "--uit",
        default=None,
        help="schrijf de uitvoer hierheen; een relatief pad staat in de uitvoermap",
    )
    beoordeel.add_argument(
        "--laad-seed",
        dest="laad_seed",
        action="store_true",
        default=True,
        help="laad de seed voor het beoordelen",
    )
    beoordeel.add_argument("--geen-seed", dest="laad_seed", action="store_false")
    beoordeel.add_argument(
        "--droog", action="store_true", help="niet opslaan, alleen berekenen en tonen"
    )
    beoordeel.add_argument(
        "--enkel-getal",
        action="store_true",
        help="vraag om één samenvattend cijfer (wordt geweigerd, met uitleg)",
    )
    beoordeel.set_defaults(func=_beoordeel)

    configuratie = subs.add_parser(
        "configuratie", help="toon welke paden uit de omgeving worden gebruikt"
    )
    configuratie.set_defaults(func=_toon_configuratie)

    argumenten = ontleder.parse_args(argv)
    try:
        return int(argumenten.func(argumenten))
    except MotorFout as fout:
        print(f"{type(fout).__name__}: {fout}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
