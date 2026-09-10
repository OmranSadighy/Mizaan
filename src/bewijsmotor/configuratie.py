"""Configuratie buiten de code (§11, fase 1).

Databasepad, seed-map en uitvoermap komen uit omgevingsvariabelen met een
zinnige standaardwaarde. Geen pad staat hardgecodeerd in de motor.

    BEWIJSMOTOR_DB        pad naar het databasebestand, of ``:memory:``
    BEWIJSMOTOR_SEED      map met kernregels, lookups, vragen en profielen
    BEWIJSMOTOR_UITVOER   map waarin beoordelingen worden weggeschreven

De standaardwaarden gelden alleen als de variabele niet gezet is. Wie een lege
waarde zet, krijgt een melding: een lege string is een vergissing, geen keuze.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .fouten import ConfiguratieFout

VARIABELE_DB = "BEWIJSMOTOR_DB"
VARIABELE_SEED = "BEWIJSMOTOR_SEED"
VARIABELE_UITVOER = "BEWIJSMOTOR_UITVOER"

_PAKKETWORTEL = Path(__file__).resolve().parents[2]
STANDAARD_DB = "bewijsmotor.sqlite3"
STANDAARD_SEED = _PAKKETWORTEL / "seed"
STANDAARD_UITVOER = Path("uitvoer")

GEHEUGEN = ":memory:"


def _lees(naam: str, standaard: str) -> str:
    ruw = os.environ.get(naam)
    if ruw is None:
        return standaard
    if not ruw.strip():
        raise ConfiguratieFout(
            f"omgevingsvariabele {naam} is gezet maar leeg. Laat haar weg om de "
            f"standaardwaarde '{standaard}' te gebruiken, of geef een pad op."
        )
    return ruw.strip()


@dataclass(frozen=True)
class Configuratie:
    databasepad: str
    seed_map: Path
    uitvoer_map: Path

    @classmethod
    def uit_omgeving(cls) -> Configuratie:
        return cls(
            databasepad=_lees(VARIABELE_DB, STANDAARD_DB),
            seed_map=Path(_lees(VARIABELE_SEED, str(STANDAARD_SEED))),
            uitvoer_map=Path(_lees(VARIABELE_UITVOER, str(STANDAARD_UITVOER))),
        )

    @property
    def database_url(self) -> str:
        if self.databasepad == GEHEUGEN:
            return "sqlite+pysqlite:///:memory:"
        return f"sqlite+pysqlite:///{self.databasepad}"

    def controleer_seed(self) -> Path:
        if not self.seed_map.is_dir():
            raise ConfiguratieFout(
                f"de seed-map '{self.seed_map}' bestaat niet. Zet {VARIABELE_SEED} op de map "
                "met kernel_rules.json, lookups.json, critical_questions.json en profielen/."
            )
        return self.seed_map

    def klaargezette_uitvoer_map(self) -> Path:
        self.uitvoer_map.mkdir(parents=True, exist_ok=True)
        return self.uitvoer_map

    def als_dict(self) -> dict[str, str]:
        return {
            VARIABELE_DB: self.databasepad,
            VARIABELE_SEED: str(self.seed_map),
            VARIABELE_UITVOER: str(self.uitvoer_map),
        }
