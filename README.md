# Bewijsmotor

Een instrument dat de **kwaliteit van bewijsvoering** achter claims beoordeelt.
Het beoordeelt geen waarheid en geen personen.

Je geeft het een gestructureerde weergave van een standpunt: de beweringen, het
bewijs, en de redeneringen die het bewijs aan de beweringen koppelen. Het laat
zien hoe sterk de onderbouwing is, waar de zwakste schakel zit, welke kritische
vragen onbeantwoord blijven, en wat het oordeel zou doen kantelen.

Het geeft nooit één cijfer. Een enkel getal verbergt precies de informatie waar
het om gaat: welke schakel zwak is en waarom.

De werktitel van het product staat nergens in deze code.

## Stand van zaken: fase 1

Gebouwd zijn het datamodel, de kernregels als records, de motor met uitsluitend
de kern, en de nultest. Wat er níet in zit staat in elk rapport onder
`voorbehouden`, en uitgebreider in `docs/conventies-fase1.md`.

De motor draait in fase 1 de stappen 1, 2, 6, 7, 10, 11 en 12 uit §6 van de
bouwspecificatie. Er komt geen taalmodel aan te pas; alle structuur is handmatig
aangeleverd als JSON.

## Aan de slag

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# schema aanmaken en de seed laden
.venv/bin/bewijsmotor init --db bewijsmotor.sqlite3

# een gestructureerd bestand beoordelen
.venv/bin/bewijsmotor beoordeel voorbeelden/kalibratie_gebed.json

# de nultest en de kalibratietest draaien
.venv/bin/python -m pytest -q
```

Vraag je om één samenvattend cijfer, dan weigert het instrument met uitleg:

```bash
.venv/bin/bewijsmotor beoordeel voorbeelden/kalibratie_gebed.json --enkel-getal
```

## Hoe het in elkaar zit

| Map | Wat er staat |
|---|---|
| `seed/` | Kernregels, lookup-vocabulaires, kritische vragen, profielen. Alle inhoud staat hier, niet in code. |
| `src/bewijsmotor/db/` | Datamodel (§5), triggers voor onveranderlijkheid en register, seed laden. |
| `src/bewijsmotor/logica/` | Formele toetsing. Kent vorm, kent geen onderwerp. |
| `src/bewijsmotor/motor/` | De stappen van §6: ontleden, verzwegen premissen, inferentie, drogredenen, zekerheid, kantelpunten, rapporteren. |
| `src/bewijsmotor/contract.py` | Het uitvoercontract, waaronder de weigering om één getal te produceren. |
| `voorbeelden/` | De invoer voor de nultest en de kalibratietest. |
| `docs/` | De keuzes die het oordeel beïnvloeden, en wat is aangenomen. |

## Uitgangspunten die het schema afdwingt

* **Regels zijn data.** Geen inhoudelijke regel staat in code. De sterkteschaal,
  de premissetypen, de argumentatieschema's, de kritische vragen en zelfs de
  koppeling tussen een soort bevinding en de kernregel die haar draagt: alles
  staat als rij in de database.
* **Geen enum voor een inhoudelijk veld.** Lookup-tabellen. Een waarde toevoegen
  is een rij toevoegen. Dit project gaat over de vraag of lijsten gesloten mogen
  zijn; dat antwoord zit niet in het schema gebakken.
* **Eén generieke relatietabel.** Relaties dragen een `relation_type`.
* **De kern is onveranderlijk.** De kernregels staan als records met
  `immutable = true` en hun zelfvernietigingsargument, en databasetriggers
  weigeren ze te wijzigen of te verwijderen.
* **Alles versioneerd.** Elke beoordeling draagt de versie van motor, contract,
  invoerschema, profiel en regelset.
* **Nooit één getal.** Gecontroleerd bij elke teruggave, en een expliciet
  verzoek om één cijfer wordt geweigerd.
* **Onvoldoende bewijs is een geldige uitkomst.**
