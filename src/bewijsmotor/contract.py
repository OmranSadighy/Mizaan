"""Het uitvoercontract.

Randvoorwaarde §2.5: nooit één getal. Dat is hier geen richtlijn maar een
gecontroleerde eigenschap. De motor weigert op twee manieren:

1. **Passief.** Elke uitvoer wordt vóór teruggave gecontroleerd. Staat er ergens
   een getal in, dan is dat een contractschending en komt de uitvoer niet naar
   buiten. Sterkte reist als label, nooit als waarde op een schaal.
2. **Actief.** Wie expliciet om één samenvattend cijfer vraagt, krijgt een fout
   met uitleg, geen benadering en geen omweg.

Booleans zijn geen getallen: ``insufficient_evidence`` mag ja of nee zijn.
"""

from __future__ import annotations

from typing import Any

from .fouten import ContractSchending, EnkelGetalGeweigerd

WEIGERINGSTEKST = (
    "Dit instrument geeft geen enkel samenvattend cijfer, ook niet bij benadering en "
    "ook niet intern. Eén getal verbergt precies de informatie waar het om gaat: welke "
    "schakel zwak is en waarom. Vraag in plaats daarvan het sterktelabel, de zwakste "
    "schakel, de openstaande kritische vragen en de kantelpunten op."
)


def weiger_enkel_getal(context: str = "") -> None:
    """Weiger een verzoek om één samenvattend cijfer."""
    aanhef = f"{context}: " if context else ""
    raise EnkelGetalGeweigerd(aanhef + WEIGERINGSTEKST)


def zoek_getallen(waarde: Any, pad: str = "$") -> list[str]:
    """Zoek elk getal in een uitvoerstructuur en geef de paden terug."""
    gevonden: list[str] = []
    if isinstance(waarde, bool):
        return gevonden
    if isinstance(waarde, (int, float)):
        gevonden.append(f"{pad} = {waarde!r}")
        return gevonden
    if isinstance(waarde, dict):
        for sleutel, deel in waarde.items():
            if isinstance(sleutel, (int, float)) and not isinstance(sleutel, bool):
                gevonden.append(f"{pad} heeft een numerieke sleutel {sleutel!r}")
            gevonden.extend(zoek_getallen(deel, f"{pad}.{sleutel}"))
        return gevonden
    if isinstance(waarde, (list, tuple)):
        for deel in waarde:
            gevonden.extend(zoek_getallen(deel, f"{pad}[]"))
        return gevonden
    return gevonden


def verifieer(uitvoer: Any) -> Any:
    """Controleer de uitvoer op het getalverbod. Geeft de uitvoer terug."""
    overtredingen = zoek_getallen(uitvoer)
    if overtredingen:
        raise ContractSchending(
            "de uitvoer bevat een getal, wat het contract verbiedt (randvoorwaarde 2.5): "
            + "; ".join(overtredingen[:10])
        )
    return uitvoer
