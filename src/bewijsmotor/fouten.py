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


class OntbrekendeKern(MotorFout):
    """De motor steunt op een kernregel die niet in de database staat.

    De kern is niet iets waar de motor omheen kan rekenen. Ontbreekt een
    kernregel, dan weigert zij te oordelen in plaats van door te gaan met een
    kern die niet compleet is.
    """
