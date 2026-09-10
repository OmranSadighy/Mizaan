# Wat is aangenomen, en waarom

De bouwspecificatie die bij de bouw beschikbaar was, eindigt bij §4.3 en §5.11.
Vier onderdelen zijn mondeling doorgegeven en niet in de tekst nagelezen. Ze zijn
gebouwd op basis van die aanwijzing. Hieronder staat per onderdeel wat er is
aangenomen, zodat de opdrachtgever het kan naleggen tegen de eigen tekst.

Alle vier zijn schemawerk. Er is voor geen ervan gedrag gebouwd dat in een
latere fase hoort.

## §1 en §4.4 — vier gebruiksvormen

**Aangenomen.** Naast toetsen en vergelijken bestaan aanvallen en verdedigen,
waarbij het systeem zelf bewijs uit een corpus haalt.

**Gebouwd.** De lookup `use_form` met vier rijen: `assess`, `compare`, `attack`,
`defend`. `assessment.use_form` verwijst ernaar. Fase 1 verwerkt uitsluitend
`assess`; de overige waarden bestaan zodat schema en register ze zonder migratie
kunnen opnemen. Er is geen code voor aanvallen of verdedigen.

**Niet aangenomen.** Of een aanval of verdediging een eigen objecttype vraagt
naast `assessment`, of dat een gebruiksvorm op de beoordeling volstaat. Nu is het
laatste gekozen. Vraagt de tekst het eerste, dan is dat een tabel erbij, geen
verbouwing.

## §4.5 — mogelijk verzwegen premisse en de interim-regel

**Aangenomen.** Twee bepalingen. Ten eerste: termdekking is een heuristiek, dus
de uitvoer luidt "mogelijk verzwegen premisse", nooit een bewering dat er een gat
is, en de rationale noemt de gebruikte toets. Ten tweede: een kritische vraag met
status `failed` plafonneert het inferentielabel op `undetermined`, als
interim-regel die in fase 2 door de nederlaaggraaf wordt vervangen.

**Gebouwd.** Beide, letterlijk. Zie `docs/conventies-fase1.md` §5 en §7. De
rationale van elk voorstel begint met "toets:" en noemt de toets bij naam. De
interim-regel noemt zichzelf interim in de rationale die de gebruiker ziet.

## §5.12 — het register

**Aangenomen.** `assessment` wordt append-only met `supersedes`, plus
`qaida_status_history` en `assessment_dependency`.

**Gebouwd.**

* `assessment` is append-only, afgedwongen met databasetriggers. Wijzigen en
  verwijderen wordt geweigerd. Een herziening is een nieuwe rij die via
  `supersedes` naar de kop van de vorige keten wijst. Twee beoordelingen horen
  bij dezelfde claim wanneer de externe verwijzing van de inzending én die van de
  claim gelijk zijn; zonder externe verwijzing op de inzending is er geen
  identiteit over runs heen en wordt niets opgevolgd.
* `qaida_status_history` wordt door een trigger geschreven, niet door de
  aanroeper. Actor en reden komen uit een contexttabel die de helper vult.
  Wijzigt iemand de status buiten de helper om, dan komt de regel er alsnog, met
  de vermelding dat er geen reden is vastgelegd. Het register hangt niet af van
  de goede wil van de aanroeper.
* `assessment_dependency` legt per beoordeling vast waarvan zij afhing: de
  kernregels met hun versie, het profiel met zijn versie, en de premissen in de
  keten. Zo is achteraf te zien welke beoordelingen meebewegen als er iets
  verandert.

**Niet aangenomen.** Of de historieregel de regelsetversie van vóór of van na de
wijziging moet dragen. Nu is gekozen voor de versie die gold op het moment van de
wijziging.

## §5.13 — de corpustabellen

**Aangenomen.** De corpustabellen worden aangemaakt en blijven leeg, zonder code.

**Gebouwd.** Vijf tabellen: `corpus_source` (met licentieveld, want er komt geen
eigen hadithdatabase), `corpus_document`, `corpus_passage`, `corpus_retrieval` en
`corpus_retrieval_hit`. Allemaal leeg. `premise.provenance_corpus_document_id`
wijst ernaar, zodat een premisse die bij aanvallen of verdedigen uit het corpus
komt, haar herkomst kan dragen zonder migratie.

`corpus_retrieval_hit` heeft een `positie` als volgordepositie. Dat is een
ordening, geen relevantiescore; de motor geeft haar nooit als beoordeling terug.

**Niet aangenomen.** De precieze tabelindeling. Als de tekst een andere indeling
voorschrijft, is dit vervangbaar zonder gevolgen voor de motor: er is geen code
die deze tabellen leest of schrijft.

## §5.2 — figuurlijke lezing nullable

**Aangenomen.** `figurative_reading_permitted` is nullable, en een bewerking die
ervan afhangt terwijl het `null` is, faalt met een melding zonder terug te vallen
op een standaardwaarde.

**Gebouwd.** De kolom is nullable, het lege profiel laat haar leeg, en
`profielinstelling()` weigert een onbepaald veld te lezen met een melding die
zegt waarom er geen standaardwaarde is. Fase 1 leest het veld nergens; de
weigering is getest.

## §5.8 — profielen breiden vragensets uit

**Aangenomen.** Het schema moet toelaten dat een profiel de vragenset van een
schema uitbreidt. Basisvragen krijgen een herkomstveld, profielvragen verwijzen
naar de qaida die ze toevoegt.

**Gebouwd.** `scheme_critical_question` draagt `origin` (`base` of `profile`),
`added_by_qaida_id` en `profile_id`. De geseede basisvragen dragen `origin =
base` en geen qaida. De motor haalt bij elke stap de basisvragen van het schema
op plus de vragen die het actieve profiel toevoegt; in fase 1 zijn dat er nul.
Het toevoegen van de masalik al-illah-vragen aan het analogieschema is later een
kwestie van rijen invoegen, niet van migreren.

## Toegevoegd buiten de veldenlijst van §5

Twee velden staan in het model die de specificatie niet noemt. Ze zijn nodig voor
gedrag dat de specificatie wél eist, en ze staan hier zodat ze te betwisten zijn.

* `premise.asserts_claim`. Zonder deze schakel loopt de zwakste-schakelregel niet
  door over de claimgrens heen, terwijl §3 een premisse toestaat die zelf een
  claim is. Zie `docs/conventies-fase1.md` §17.
* `assessment.use_form`. Draagt de gebruiksvorm uit §4.4 zodat aanvallen en
  verdedigen later zonder migratie passen.

Verder is de lookup `relation_type` uitgebreid met `relies_on`, voor de
verwijzing van een interpretatie naar een qaida (§4.3: interpretaties verwijzen,
ze dupliceren niet). Omdat relatiesoorten data zijn, is dat een rij en geen
schemawijziging.
