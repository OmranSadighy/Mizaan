"""De interim-regels van fase 1 (§4.5).

Deze regels gelden alleen in fase 1 en worden vervangen zodra het genoemde
mechanisme bestaat. Ze staan hier als één bron van waarheid: de motor neemt ze
op in elke beoordeling, en de verwijderplicht uit §4.5 bewaakt ze.

**Verwijderplicht.** Elke regel hier krijgt een test die faalt zodra het
vervangende mechanisme bestaat en de regel er nog is. Zie
``tests/test_interim_verwijderplicht.py``. Een interim-regel die stil blijft
staan is de meest voorspelbare fout in een gefaseerd bouwplan.

De sporen die de bewaking zoekt staan bewust niet hier maar in de test: het is
een testconcern, en de motor heeft er tijdens het rekenen niets aan.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InterimRegel:
    sleutel: str
    naam: str
    werking: str
    vervalt_in: str
    vervangen_door: str
    toegepast_in: tuple[str, ...]
    spec: str = "§4.5"

    def als_dict(self) -> dict[str, str]:
        return {
            "regel": self.naam,
            "spec": self.spec,
            "werking": self.werking,
            "vervalt": self.vervalt_in,
            "vervangen_door": self.vervangen_door,
            "toegepast_in": ", ".join(self.toegepast_in),
        }


INTERIM_REGELS: tuple[InterimRegel, ...] = (
    InterimRegel(
        sleutel="gefaalde_kritische_vraag",
        naam="gefaalde kritische vraag",
        werking=(
            "een kritische vraag met status 'gefaald' plafonneert het label van de inferentie "
            "op onbepaald, en de rationale noemt de vraag"
        ),
        vervalt_in="fase 2",
        vervangen_door="de nederlaaggraaf met grounded semantics uit B3",
        toegepast_in=("motor/berekening.py",),
    ),
    InterimRegel(
        sleutel="convergente_steun",
        naam="convergente steun",
        werking=(
            "binnen een bewijslijn geldt het minimum, over onafhankelijke lijnen heen het "
            "maximum; geen verhoging door convergentie"
        ),
        vervalt_in="fase 2",
        vervangen_door=(
            "noisy-OR met de afbeelding van labels op kansen als qaida met eigen bewijs"
        ),
        toegepast_in=("motor/berekening.py",),
    ),
    InterimRegel(
        sleutel="verzwegen_premissen",
        naam="verzwegen premissen",
        werking=(
            "structurele detectie via vormaanvulling en termdekking; termdekking is een "
            "heuristiek en de uitvoer luidt 'mogelijk verzwegen premisse'"
        ),
        vervalt_in="fase 5",
        vervangen_door="de taalmodelstap die verzwegen premissen voorstelt, met de poorten uit B4",
        toegepast_in=("logica/vorm.py", "motor/engine.py"),
    ),
)

REGELS_OP_SLEUTEL: dict[str, InterimRegel] = {regel.sleutel: regel for regel in INTERIM_REGELS}
