# Verschillen tussen de aannames van fase 1 en de herziene specificatie

Fase 1 is gebouwd op een verouderde versie van de bouwspecificatie, die eindigde
bij §4.3 en §5.11. Vier onderdelen zijn destijds mondeling doorgegeven en door
mij ingevuld. Dit document zet per onderdeel naast elkaar wat ik aannam en wat
de herziene tekst zegt, en wat ik daarmee heb gedaan.

Waar mijn indeling naar mijn oordeel beter is dan de tekst, staat dat er met
argument bij, zodat de opdrachtgever kan kiezen tussen de spec aanpassen of mijn
code aanpassen. Waar de tekst concreet is en mijn keuze willekeurig was, is
gewoon gelijkgetrokken.

---

## Kort overzicht

| Onderdeel | Aanname | Herziene tekst | Gedaan |
|---|---|---|---|
| §1 gebruiksvormen | vier waarden in een lookup | vier, mét fasetoewijzing | gelijkgetrokken, fase is nu data |
| §4.4 aanvallen/verdedigen | alleen schema-eis | vijf inhoudelijke eisen | schema dekt ze; gedrag komt later |
| §4.5 interim-regels | drie regels, één gemarkeerd | drie regels, alle te markeren | alle drie gemarkeerd met §4.5 |
| §5.6 provenance | eigen namen, vijf waarden | vier vaste waarden | gelijkgetrokken |
| §5.6 corpusverwijzing | naar een document | `retrieval_ref` naar een sessie | gelijkgetrokken |
| §5.8 herkomst van vragen | `base` / `profile` | herkomstbron, bv. `walton_2008` | beide, zie hieronder |
| §5.12 `superseded_by` | niet aanwezig | kolom naast `supersedes` | als view, zie hieronder |
| §5.12 `stale` | niet aanwezig | verplicht veld | toegevoegd |
| §5.12 aanleiding | niet aanwezig | `triggering_assessment_ref` | toegevoegd |
| §5.12 overzichten | niet aanwezig | vier views | toegevoegd |
| §5.12 afhankelijkheidssoort | ook `kernel_rule` | vier soorten genoemd | behouden, zie hieronder |
| §5.13 corpustabellen | vijf eigen tabellen | drie benoemde tabellen | gelijkgetrokken |
| §10 containerisatie | niets gebouwd | verboden vóór fase 3 | voldoet |
| §11 afhankelijkheden | versiebereiken | exacte versies plus lockfile | gelijkgetrokken |
| §11 configuratie | pad in code | omgevingsvariabelen | gelijkgetrokken |

---

## 1. Gebruiksvormen (§1)

**Aangenomen.** Vier waarden `assess`, `compare`, `attack`, `defend` in een
lookup, en in code een constante die zei dat fase 1 alleen `assess` uitvoert.

**Tekst.** Dezelfde vier, maar met een fasetoewijzing: toetsen hoort bij fase 1,
vergelijken bij fase 6, aanvallen en verdedigen bij "later" en worden niet in dit
bouwplan gebouwd.

**Gedaan.** De fase staat nu als data bij de gebruiksvorm. De motor kent alleen
haar eigen fase en weigert een vorm die zij nog niet uitvoert. Daarmee is de
fasegrens uit de code verdwenen, en de melding verschilt: vergelijken hoort bij
het bouwplan en komt in fase 6, aanvallen hoort er niet bij.

Dit is een verbetering die uit de tekst volgt en niet uit mijn eigen inzicht:
zonder de tabel in §1 had ik geen reden om onderscheid te maken.

## 2. Aanvallen en verdedigen (§4.4)

**Aangenomen.** Alleen dat het schema de twee functies zonder migratie moet
kunnen opnemen.

**Tekst.** Vijf eisen: zelfde motor, symmetrie, eerlijkheid over de eigen
uitkomst, herkomst van de zoektocht, en de verhouding tot steelmanning.

**Gedaan.** Vier van de vijf raken alleen het schema en zijn gedekt:
`retrieval_session` legt vast wat is doorzocht, met welke zoekvraag en wat niet
is gevonden, en `provenance` onderscheidt een opgehaalde van een aangeleverde
premisse. "Zelfde motor" en "symmetrie" zijn eisen aan gedrag dat nog niet
bestaat; er is één beoordelingspad en dat blijft zo.

**Wat nog niet gedekt is.** "Eerlijkheid over de eigen uitkomst" vraagt dat de
uitvoer onderscheid maakt tussen "dit aangeleverde argument steunt X zwak" en
"de sterkste onderbouwing die ik voor X kan vinden is zwak". Het eerste zegt de
motor nu al met zoveel woorden. Het tweede vraagt een veld op de beoordeling dat
zegt of er gezocht is. Dat veld hoort bij de fase waarin gezocht wordt, en staat
als open item.

## 3. Interim-regels (§4.5)

**Aangenomen.** De twee regels die mondeling waren doorgegeven, plus de
convergentieregel die uit ons gesprek volgde. Alleen de eerste was in code als
interim gemarkeerd.

**Tekst.** Drie regels, met de opdracht ze in de code te markeren met een
verwijzing naar §4.5.

**Gedaan.** Alle drie dragen nu de verwijzing, op de plek waar ze worden
toegepast én in de uitvoer van elke beoordeling onder `interim_regels`, met wat
de regel doet en wanneer zij vervalt.

## 4. Herkomst van een premisse (§5.6)

**Aangenomen.** Vijf waarden met eigen namen: `submitted_by_user`,
`retrieved_from_corpus`, `proposed_by_engine`, `proposed_by_llm`, `imported`.

**Tekst.** Vier vaste waarden: `user_supplied`, `engine_retrieved`,
`llm_proposed`, `engine_inferred`. Plus `retrieval_ref`, alleen bij
`engine_retrieved`.

**Gedaan.** Gelijkgetrokken, inclusief het laten vallen van `imported`. Mijn
namen waren willekeurig en de tekst is expliciet. `imported` was overbodig:
`proposed_by` draagt al `import`, en dat zegt wie de structuur aanleverde, wat
iets anders is dan waar het materiaal vandaan komt.

Mijn corpusverwijzing wees naar een document. De tekst wijst naar de zoeksessie,
en dat is beter: het verbindt de premisse met de zoekvraag en met wat er niet
gevonden is, precies wat §4.4 eist.

## 5. Herkomst van een kritische vraag (§5.8)

**Aangenomen.** Een veld `origin` met waarden `base` en `profile`, om
basisvragen te onderscheiden van vragen die een profiel toevoegt.

**Tekst.** "Basisvragen krijgen een herkomstveld (bv. `walton_2008`),
profielvragen verwijzen naar de qaida die ze toevoegt."

**Gedaan.** Beide, want het zijn twee verschillende dingen. `origin` stuurt het
gedrag: een basisvraag hoort bij het schema, een profielvraag bij een qaida.
`herkomst_bron` is bronvermelding: waaraan de vraag ontleend is. De geseede
vragen dragen `walton_2008`, behalve de vragen bij het deductieve schema, die
`klassieke_logica` dragen omdat ze niet van Walton komen.

**Mogelijke aanpassing van de spec.** Als u met "herkomstveld" precies dit
bedoelde, dan is de tekst compleet en heb ik hem goed gelezen. Bedoelde u er het
onderscheid base/profile mee, dan is er een tweede veld nodig, want de
bronvermelding kan dat onderscheid niet dragen.

## 6. `superseded_by` (§5.12)

**Tekst.** "Voeg `supersedes` en `superseded_by` toe."

**Gedaan.** `supersedes` is een kolom. `superseded_by` is een view.

**Waarom afwijkend.** Dezelfde paragraaf zegt dat `assessment` append-only is en
nooit wordt overschreven. Een kolom `superseded_by` op de oudere rij vullen is
precies wel terugschrijven op een rij die al bestaat. De twee eisen kunnen niet
allebei letterlijk gelden.

De verwijzing vooruit is exact af te leiden uit de verwijzing terug: de opvolger
is de rij wier `supersedes` naar deze wijst. Er gaat dus geen informatie
verloren, en de append-only garantie blijft hard afgedwongen door
databasetriggers. Het overzicht `v_beoordeling_keten` geeft beide richtingen.

**Als u de kolom toch wilt**, dan moet de trigger één uitzondering krijgen: het
eenmalig vullen van `superseded_by` wanneer die nog leeg is. Dat is te doen, maar
het verzwakt de garantie die de rest van de paragraaf vraagt. Mijn voorstel is de
spec op dit punt aan te passen naar "`superseded_by` is af te leiden en wordt als
overzicht aangeboden".

## 7. Afhankelijkheidssoorten (§5.12)

**Tekst.** `depends_on_kind` met vier waarden: qaida, interpretation, premise,
profile.

**Gedaan.** De lookup kent die vier en daarnaast `kernel_rule`, en de motor legt
per beoordeling vast op welke kernregels zij steunde, met hun versie.

**Waarom.** Kernregels zijn versioneerde records waar het oordeel echt van
afhangt. Verandert er een, dan is precies dat de wijziging waarvan §5.12 zegt dat
het systeem moet kunnen melden welke beoordelingen verouderd zijn. Zonder deze
soort zou een kernregelwijziging onzichtbaar blijven in het register.

**Voorstel.** Neem `kernel_rule` op in de opsomming in §5.12.

## 8. Corpustabellen (§5.13)

**Aangenomen.** Vijf tabellen van eigen makelij: `corpus_source`,
`corpus_document`, `corpus_passage`, `corpus_retrieval`, `corpus_retrieval_hit`.

**Tekst.** Drie benoemde tabellen: `corpus_source` met `name`, `kind`, `license`
en `access_method`; `corpus_entry` met `source_ref`, `locator`, `text` en
`language`; `retrieval_session` met `mode`, `claim_ref`, `corpus_scope[]`,
`query`, `executed_at`, `found[]` en `not_found_note`.

**Gedaan.** Gelijkgetrokken, zoals afgesproken. Twee kanttekeningen:

* `corpus_scope[]` en `found[]` zijn lijsten. Ze staan als eigen tabellen
  (`retrieval_session_scope` en `retrieval_session_found`) in plaats van als
  lijst in één kolom, zodat de verwijzing naar een bron of een ingang een echte
  vreemde sleutel is. Een lijst in een kolom zou later stilzwijgend naar een
  verwijderde ingang kunnen wijzen.
* `mode` verwijst naar de gebruiksvormlookup. De spec noemt `attack | defend`;
  door naar dezelfde lookup te wijzen blijft er één lijst van gebruiksvormen in
  plaats van twee die uit elkaar kunnen lopen.

## 9. Containerisatie (§10)

Er is niets gecontaineriseerd: geen Dockerfile, geen compose-bestand, geen
image. Fase 1 draait als gewone Python-omgeving. Dit is de enige nieuwe regel in
§10 en er was niets te herstellen.

## 10. Afhankelijkheden en configuratie (§11)

**Aangenomen.** Versiebereiken (`SQLAlchemy>=2.0`) en een seed-pad dat uit de
pakketstructuur werd afgeleid.

**Tekst.** Exacte versies plus een lockfile; databasepad, seed-map en uitvoermap
als omgevingsvariabelen met een zinnige standaard.

**Gedaan.** `requirements.lock` pint dertien pakketten, inclusief alle
transitieve, elk met een sha256-inhoudshash; installeren gebeurt met
`--require-hashes`. `pyproject.toml` bevat geen enkel bereik meer, ook niet voor
de build-backend. De drie paden komen uit `BEWIJSMOTOR_DB`, `BEWIJSMOTOR_SEED` en
`BEWIJSMOTOR_UITVOER`; een test bewijst dat er nergens anders in de motor een pad
staat.

Een lege waarde is een fout en geen keuze: wie `BEWIJSMOTOR_SEED=""` zet, krijgt
een melding in plaats van stilzwijgend de standaard.

---

## Aannames die de tekst heeft bevestigd

Deze had ik goed gelezen en er is niets aan veranderd:

* `figurative_reading_permitted` is nullable, en een bewerking die ervan afhangt
  faalt met een melding zonder terugval op een standaardwaarde. De tekst zegt dit
  nu letterlijk.
* De drie interim-regels werken zoals ik ze had gebouwd: de gefaalde vraag
  plafonneert, de onbeantwoorde vraag verlaagt niets, minimum binnen een lijn en
  maximum erover, en termdekking is een heuristiek die nooit een gat beweert.
* Schema's en hun vragensets zijn seed-data en een profiel kan een vragenset
  uitbreiden.
* `assessment` is append-only en `assessment_dependency` legt per beoordeling
  vast waarvan zij afhing.
* De twee velden die ik buiten §5 had toegevoegd, `premise.asserts_claim` en
  `assessment.use_form`, zijn door de opdrachtgever overgenomen.
