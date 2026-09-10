"""Fouten van de motor. Elke fout noemt waar zij op steunt."""


class MotorFout(Exception):
    """Basisklasse voor alle fouten van de motor."""


class InvoerFout(MotorFout):
    """De aangeleverde structuur is niet verwerkbaar."""


class OngedefinieerdeVerwijzing(InvoerFout):
    """Er wordt geoordeeld over iets dat niet bepaald is.

    Steunt op de kernregel ``oordeel_vereist_begrip``.
    """

    kernregel = "oordeel_vereist_begrip"


class OnbekendeLookupwaarde(InvoerFout):
    """Een waarde staat niet in de lookup-tabel die haar vocabulaire bevat."""


class EnkelGetalGeweigerd(MotorFout):
    """Er is om één samenvattend getal gevraagd.

    Steunt op randvoorwaarde §2.5: een enkel eindcijfer is verboden in elke
    laag, ook intern in de API.
    """


class ContractSchending(MotorFout):
    """De uitvoer voldoet niet aan het uitvoercontract."""


class OnbepaaldeProfielinstelling(MotorFout):
    """Een bewerking hangt af van een profielinstelling die niet bepaald is.

    De motor valt niet terug op een standaardwaarde, want elke standaardwaarde
    is al een standpunt.
    """


class OnveranderlijkRecord(MotorFout):
    """Er is geprobeerd een onveranderlijk record te wijzigen of te verwijderen."""
