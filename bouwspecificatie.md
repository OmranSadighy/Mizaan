# Bouwspecificatie — Mizan (werktitel)

> Dit document beschrijft **wat** gebouwd moet worden, niet **hoe**. Technologiekeuzes zijn vrij binnen de randvoorwaarden van §2. Elke fase heeft acceptatiecriteria; een fase is klaar als alle criteria aantoonbaar gehaald zijn. Bouw geen fase vooruit. Waar dit document een beslissing vastlegt, is die genomen: wijk er niet van af zonder de opdrachtgever te vragen.

De naam "Mizan" is een werktitel en kan veranderen. Gebruik hem nergens hardgecodeerd.

---

## 1. Doel

Een instrument dat een aangeleverde tekst — onderzoek, standpunt, fatwa, mening, uitspraak — ontleedt in beweringen, bewijzen en redeneringen, en per onderdeel en als geheel toont:

- hoe sterk de onderbouwing is,
- waar de zwakste schakel zit,
- welke kritische vragen onbeantwoord blijven,
- wat het oordeel zou veranderen.

Het instrument kent vier gebruiksvormen. De beoordelingsmachine is in alle vier **identiek**; wat verschilt is uitsluitend de herkomst van de premissen.

| # | Functie | Herkomst premissen | Fase |
|---|---|---|---|
| 1 | **Toetsen** — één claim beoordelen | aangeleverd door de gebruiker | 1 |
| 2 | **Vergelijken** — twee of meer claims naast elkaar | aangeleverd door de gebruiker | 6 |
| 3 | **Aanvallen** — de sterkste tegenwerping zoeken | door het systeem opgehaald uit een corpus | later |
| 4 | **Verdedigen** — de sterkste onderbouwing zoeken | door het systeem opgehaald uit een corpus | later |

Functies 3 en 4 worden **niet** in dit bouwplan gebouwd. Het schema moet ze wel zonder migratie kunnen opnemen; zie §5.12, §5.13 en §4.4.

Het instrument beoordeelt de **kwaliteit van bewijsvoering**. Het beoordeelt geen waarheid en geen personen.

---

## 2. Niet-onderhandelbare randvoorwaarden

1. **Eén motor, verwisselbare instrumenten.** Er is één beoordelingsproces voor alle soorten claims. Domeinverschillen zitten uitsluitend in (a) meetinstrumenten die premissesterkte leveren en (b) instelbare regels. Er zijn geen aparte rubrics per domein.
2. **Regels zijn data.** Geen inhoudelijke regel staat in code. Alles wat een oordeel stuurt, staat in de database als record met eigen bewijs, en is te wijzigen zonder code aan te raken.
3. **Kern minimaal, expliciet, onveranderlijk.** De kernregels staan óók als records, gemarkeerd `immutable = true`, met als bewijs het zelfvernietigingsargument (§4.2). De motor weigert ze te laten vallen, maar toont wél elk conflict ermee.
4. **De AI stelt voor, de motor rekent.** Elke uitvoer van een taalmodel is een voorstel met betrouwbaarheidsscore. De motor rekent uitsluitend over bevestigde of hoog-betrouwbare structuur.
5. **Nooit één getal.** Uitvoer bestaat altijd uit meerdere assen, een aangewezen zwakste schakel, openstaande kritische vragen en kantelpunten. Een enkel eindcijfer is verboden in elke laag, ook intern in de API.
6. **Onvoldoende bewijs is een geldige uitkomst.** De motor weigert te scoren als bronnen ontbreken en zegt dat expliciet.
7. **Geen oordeel over personen.** Zie §9.
8. **Alles versioneerd.** Elke beoordeling verwijst naar de versie van het profiel, de regelset en de motor waarmee hij is gemaakt, zodat hij reproduceerbaar en uitlegbaar blijft.
9. **Geen enums voor inhoudelijke velden.** Lookup-tabellen. Dit project gaat over de vraag of lijsten gesloten mogen zijn; bak dat antwoord niet in het schema.
10. **Eén generieke relatietabel.** Relaties tussen regels (afhangen van, aanvallen, steunen) zijn rijen met een `relation_type`, geen aparte kolommen of tabellen per relatie.

---

## 3. Definities

| Term | Betekenis |
|---|---|
| **Claim** | Eén propositie. Een ingediende tekst levert meerdere claims op. |
| **Premisse** | Een bewering waarop een claim steunt. Kan recursief zijn: een premisse kan zelf premissen hebben. |
| **Bron** | De tekst of bron waaraan een premisse is ontleend (vers, hadith, studie, uitspraak van een geleerde). |
| **Interpretatie** | Een claim over wat een tekst betekent. Zelf een beoordeelbaar object met eigen gronden en sterkte. |
| **Inferentie** | De stap van premissen naar conclusie. Heeft een schema-type en een vaste set kritische vragen. |
| **Qaida** (mv. qawa'id) | Een instelbare regel die een parameter van de motor zet: prior, bewijslast, reikwijdte, precedentie, drempel of conflictvolgorde. |
| **Profiel** | Een versioned bundel van instellingen en actieve qawa'id. Bijvoorbeeld "hanafitisch", "ahl al-hadith", "empirisch-wetenschappelijk". |
| **Competentieniveau** | Het niveau van degene voor wie het oordeel wordt berekend. Standaard "onbeperkt" (volledige weging). |
| **Instrument** (plugin) | Meet de sterkte van één soort premisse en levert gestandaardiseerde uitvoer. Kan een deelgraaf teruggeven. |
| **Beoordeling** | De uitvoer van de motor voor één claim onder één profiel en één competentieniveau. |
| **Vergelijking** | De uitvoer van de motor voor twee of meer claims naast elkaar. |
| **Sterkte** | Altijd een ordinaal label: `certain > strong > probable > weak > undetermined`. Nooit een kaal getal. |

---

## 4. Vastgelegde beslissingen

### 4.1 De vijf ontwerpbeslissingen

**B1 — Bewijslast is een profielinstelling.** Veld `burden_allocation` op `profile`. Waarden: `claimant` | `departer_from_status_quo` | `affirmer_if_evidenced`. Standaard `claimant`. Zit **niet** in de kern.

**B2 — Vaste evaluatievolgorde.** De motor doorloopt altijd, in deze volgorde:
1. thubut per premisse (is de bron vastgesteld),
2. status per tekst (afgeschaft, meerduidig, etc.),
3. dalalah per premisse (zegt de bron wat beweerd wordt),
4. inferentie (volgt de conclusie),
5. conclusie (zwakste schakel, convergente steun, kantelpunten).

Geen stap mag een latere stap raadplegen. Cykeldetectie moet deze volgorde als toegestaan kennen.

**B3 — Aanvalsemantiek.** Een aanval slaagt alleen als het sterktelabel van de aanvaller **niet lager** is dan dat van het doelwit; een geslaagde aanval heet een nederlaag. Op de nederlaaggraaf draait **grounded semantics** (Dung): unieke uitkomst, sceptisch, bij wederzijdse nederlaag "onbeslist". Gebruik een bestaande bibliotheek; bouw dit niet zelf. Een nederlaag zet de **status** van het doelwit op `defeated`; hij verlaagt **niet** de sterkte. Status en sterkte zijn aparte assen.

**B4 — AI-grens.** Twee LLM-beslissingen krijgen altijd een bevestigingspoort vóór de motor ermee rekent: `premise_type` en `scheme`. Alle overige voorstellen mogen automatisch door bij `confidence ≥ threshold` (instelbaar; standaard 0,85). Elk LLM-voorstel wordt opgeslagen mét confidence en met de aanduiding `proposed` tot het bevestigd is.

**B5 — Eenheid en vergelijking.** Claim = één propositie. Vergelijking is een eigen object (§5.10).

### 4.2 Kerncriterium

Een regel hoort in de kern als en alleen als het ontkennen ervan de ontkenning zelf onmogelijk maakt. Toepassing:

| Regel | Kern? | Reden |
|---|---|---|
| non-contradictie | ja | de ontkenning gebruikt de regel |
| oordeel vereist begrip van de zaak | ja | een ontkenning over iets ongedefinieerds heeft geen inhoud |
| zwakste schakel: conclusie ≤ zwakste premisse of inferentie | ja | anders ontstaat zekerheid uit niets |
| geldige vorm ≠ ware premisse | ja | vormfout en inhoudsfout zijn onderscheidbaar of niets is |
| elke bewering vereist steun en de bewijslast moet expliciet gealloceerd zijn | ja | zonder dit is elke uitspraak gratis, inclusief deze |
| *welke* allocatie geldt | **nee** | drie coherente allocaties bestaan naast elkaar (B1) |
| Ockham, "buitengewone claims", falsifieerbaarheid als demarcatie | nee | ontkenbaar zonder zelfvernietiging |
| alle islamitische qawa'id, alle domeindrempels, alle bronhiërarchieën | nee | configuratie |

### 4.3 Consistentieregels

- Een competentie-gebonden regel mag een premisse **herclassificeren** (bv. "lekenlezing van een hadith → lage betrouwbaarheid"); hij mag een geldige defeater **niet onderdrukken**. Anders breekt de zwakste-schakelregel.
- Interpretaties **verwijzen** naar qawa'id; ze dupliceren ze niet.
- De motor beoordeelt het argument **zoals aangeleverd**. Steelmanning (de sterkste versie van een argument construeren) is een aparte, expliciet aan te zetten stap, en de uitvoer maakt altijd onderscheid tussen "dit argument steunt X zwak" en "X is zwak".
- Dialectische kracht wordt **op aanvraag** berekend tegen een opgegeven profiel, niet vooraf tegen alle.

### 4.4 Aanvallen en verdedigen (functies 3 en 4)

Deze functies worden nu niet gebouwd. Onderstaande eisen gelden vanaf het moment dat ze wel gebouwd worden, en bepalen nu al het schema.

- **Zelfde motor.** Opgehaalde premissen doorlopen exact dezelfde beoordeling als aangeleverde. Er komt geen tweede beoordelingspad.
- **Symmetrie.** Elke claim die aangevallen kan worden, moet met identieke machinerie verdedigd kunnen worden. Een asymmetrische implementatie is een blokkerende fout.
- **Eerlijkheid over de eigen uitkomst.** Het systeem moet kunnen rapporteren dat de sterkste gevonden aanval zwak is, of de sterkste gevonden verdediging. De uitvoer is een beoordeling, geen pleidooi.
- **Herkomst van de zoektocht.** Elke sessie legt vast welk corpus is doorzocht, met welke zoekvraag, en wat niet is gevonden. "Geen sterke aanval gevonden" en "niet gezocht" zijn verschillende uitkomsten en moeten in de uitvoer verschillen.
- **Verhouding tot steelmanning.** Functies 3 en 4 zíjn de steelman-stap uit §4.3, in twee richtingen. De uitvoer maakt daarom altijd onderscheid tussen "dit aangeleverde argument steunt X zwak" en "de sterkste onderbouwing die ik voor X kan vinden is zwak".

### 4.5 Interim-regels voor fase 1

Deze regels gelden **alleen** in fase 1 en worden vervangen zodra het genoemde mechanisme bestaat. Markeer ze in de code als interim, met verwijzing naar deze paragraaf.

**Verwijderplicht.** Elke interim-regel krijgt een test die faalt zodra het vervangende mechanisme bestaat en de interim-regel er nog is. Een interim-regel die stil blijft staan is de meest voorspelbare fout in een gefaseerd bouwplan; deze test is de enige betrouwbare bewaking ertegen.

- **Gefaalde kritische vraag.** Een kritische vraag met status `failed` plafonneert het label van de inferentie op `undetermined`, en de rationale noemt de vraag. Reden: zonder de aanvalsgraaf zou de motor anders een inferentie als sterk rapporteren die hij zelf als gebroken heeft gemarkeerd, en dat is tegenstrijdige uitvoer. Een `unanswered` vraag verlaagt niets; die wordt alleen gerapporteerd als open vraag en kantelpunt. Vervalt in fase 2, wanneer B3 de nederlaaggraaf levert.
- **Convergente steun.** Binnen één bewijslijn geldt minimum over de keten; over onafhankelijke lijnen heen geldt maximum. Geen verhoging door convergentie. Reden: noisy-OR vereist een afbeelding van labels op kansen, en die afbeelding is een qaida. Vervalt in fase 2.
- **Verzwegen premissen.** Detectie gebeurt structureel: bij deductieve inferenties met opgegeven vorm door te bepalen welke premisse ontbreekt voor een geldig patroon, en bij overige inferenties door termdekking (een term in de conclusie die in geen enkele premisse voorkomt). Termdekking is een **heuristiek**, geen bewijs: de uitvoer luidt "mogelijk verzwegen premisse" en de rationale noemt de gebruikte toets. Het systeem beweert nooit dat er een gat is. Vervalt of wordt aangevuld in fase 5.

---

## 5. Datamodel — wat opgeslagen moet kunnen worden

Velden zijn beschrijvend; namen mogen afwijken, betekenis niet. Elke score is een object `{label, rationale, computed_by, version}`.

### 5.1 `kernel_rule`
`statement`, `self_refutation_argument`, `immutable = true`. Vier tot vijf rijen (§4.2). Nooit verwijderbaar via de applicatie.

### 5.2 `profile` (versioned)
`name`, `version`, `type_set[]` (welke premissetypen bestaan), `type_set_exhaustive` (bool), `type_ceilings{}` (maximaal haalbaar sterktelabel per type), `qaida_set[]`, `competence_levels[]` (naam + welke qawa'id per niveau actief zijn), `figurative_reading_permitted` (**nullable** bool), `conflict_order[]` (volgorde van conflictresolutie), `burden_allocation` (B1).

`figurative_reading_permitted` is nullable omdat zowel `true` als `false` een inhoudelijk standpunt is; `null` betekent niet-geconfigureerd. Een bewerking die van dit veld afhangt terwijl het `null` is, faalt met een duidelijke melding en valt **niet** stilzwijgend terug op een standaardwaarde.

Bij laden van een profiel: **validatie** dat elk type een bepaald plafond heeft. Een type met onbepaald plafond is een laadfout.

### 5.3 `qaida`
`statement` (AR / NL / EN), `function` (prior | burden | scope | precedence | threshold | conflict_order), `scope` (op welke gevallen de regel van toepassing is; verplicht), `evidence[]` (recursief: verwijst naar premissen), `own_strength`, `effective_strength` (= min van eigen sterkte en die van alle ouders via `depends_on`), `derivation_method` (nass | ijma | istiqra | takhrij_al_furu | rational_axiom), `status` (active | contested | rejected | conflicts_with_kernel | not_independently_decidable | defeated).

### 5.4 `edge` (generiek)
`from_id`, `to_id`, `from_kind`, `to_kind`, `relation_type` (depends_on | attacks | supports). Doelwit kan een qaida, een taxonomie-entry of een domeinpartitie zijn.

### 5.5 `premise_type` (per profiel)
Tabel, geen enum. Minstens: revelation_text, transmitted_report, consensus_claim, sense_observation, empirical_study, rational_intuition, expert_testimony. Profielen mogen typen toevoegen of weglaten.

### 5.6 `premise`
`text`, `type` (→ 5.5), `explicit` (bool), `sub_premises[]` (recursief), `thubut` (score), `dalalah` (score), `status` `{label, opposition}` — het label draagt altijd de tegenstelling waarin het gebruikt wordt (bv. `muhkam` tegenover `mutashabih` is iets anders dan `muhkam` tegenover `mansukh`), `citation` `{source_ref, verification_status: verified | unverified | corrected | disputed}`, `instrument_output` (ruwe plugin-uitvoer), `provenance` (user_supplied | engine_retrieved | llm_proposed | engine_inferred), `retrieval_ref` (→ 5.13, alleen bij `engine_retrieved`), `proposed_by` (llm | user | import | engine), `confirmed` (bool).

`provenance` is verplicht en wordt nooit afgeleid uit een ander veld. Het is de enige manier om later een opgehaalde premisse (functies 3 en 4) te onderscheiden van een aangeleverde. In fase 1 heeft elke premisse `user_supplied` of `engine_inferred` (bij een voorgestelde verzwegen premisse).

### 5.7 `interpretation`
`text_ref`, `proposed_meaning`, `grounds[]` — elk met `kind` (lexical | context | parallel_text | qarina) en eigen score, `relied_on_qawaid[]`, `supporters[]` (namen van wie deze lezing aanhing; **telt niet mee in de score**; dient als ta'yid), `strength`.

### 5.8 `inference`
`from[]` (premissen), `to` (claim of subconclusie), `scheme` (expert_opinion | analogy | precedent | sign | consequences | practical_reasoning | ignorance_or_silence | inconsistent_commitment | deductive), `interpretation_ref` (**verplicht** wanneer `from` een tekstpremisse bevat; ontbreekt hij, dan is er een verzwegen premisse en stopt de motor met een melding), `critical_questions[]` — elk `{question, status: answered | unanswered | failed, effect: undercut | undermine | none}`, `strength`.

Schema's en hun standaard vragensets zijn **seed-data**, geen code. Het schema moet toelaten dat een profiel de vragenset van een schema **uitbreidt**: qiyas voegt later de masalik al-illah-vragen toe aan het analogieschema. Dit nu regelen is goedkoop; later is het een migratie.

Een kritische vraag draagt daarom **twee** velden, die verschillende dingen doen:

- `origin` (base | profile) — stuurt gedrag: een basisvraag hoort bij het schema zelf en geldt altijd, een profielvraag geldt alleen wanneer het toevoegende profiel actief is.
- `source_ref` — zegt waaraan de vraag ontleend is: een literatuurverwijzing bij een basisvraag (bv. `walton_2008`), of een verwijzing naar de qaida die haar toevoegt bij een profielvraag.

Eén veld kan beide niet dragen: een bronvermelding zegt niets over of de vraag altijd geldt.

### 5.9 `assessment`
`claim_ref`, `profile_version`, `competence_level`, `engine_version`, `probative_force` (score), `dialectical_force[]` `{against_profile, score}`, `falsifiability_exposure` (hoeveel de claim uitsluit; los van sterkte), `weakest_element` (verwijzing), `open_critical_questions[]`, `fallacies[]`, `tipping_points[]` `{element, current_label, change_needed, would_flip_to}`, `insufficient_evidence` (bool + uitleg).

### 5.10 `comparison`
`claim_refs[]` (twee of meer), `shared_premises[]`, `divergence_points[]` — per punt: `{proposition, side_a_grounds, side_b_grounds, testable_on_text (bool), deciding_question}`, `scope_relation` (disjoint | subset | overlap | identical), `profile_version`.

### 5.11 `audit_log`
Elke wijziging aan qaida, profiel of kernel_rule, met wie, wanneer, waarom.

### 5.12 Register — wat het systeem over zichzelf bijhoudt

Het instrument houdt bij wat het heeft getoetst en wat daaruit is voortgekomen. Dit is geen logboek maar een groeiend kennisbestand; het is de reden dat een gebruiker later kan zien welke stelregels de toets hebben doorstaan en welke niet.

**`assessment` is append-only.** Een herbeoordeling maakt een nieuwe rij en overschrijft nooit. Alleen zo blijft zichtbaar hoe een oordeel veranderde toen een regel werd bijgesteld. De nieuwe rij krijgt `supersedes` (verwijzing naar de vorige beoordeling van dezelfde claim onder hetzelfde profiel); die wordt bij het invoegen geschreven en raakt de oudere rij niet.

`superseded_by` is **geen kolom maar een afgeleid overzicht**. Een kolom zou een terugschrijfactie op de oudere rij vereisen en daarmee de append-only-garantie breken voor precies het veld dat die garantie moet documenteren. De vooruitverwijzing is exact af te leiden uit `supersedes`, dus er gaat niets verloren.

**`qaida_status_history`** — `qaida_ref`, `from_status`, `to_status`, `changed_at`, `reason`, `triggering_assessment_ref` (optioneel), `changed_by`. Hiermee is te beantwoorden: welke regels zijn voorgesteld, welke zijn getoetst, welke hebben het overleefd, welke zijn afgevallen en waarop. Elke statuswijziging schrijft hier een rij; het `status`-veld op `qaida` is slechts de huidige stand.

**`assessment_dependency`** — `assessment_ref`, `depends_on_kind` (qaida | interpretation | premise | profile | kernel_rule), `depends_on_ref`, `depends_on_version`. Bij het berekenen van een beoordeling registreert de motor elk element waarop de uitkomst steunt. Daarmee kan het systeem na een wijziging melden welke eerdere beoordelingen verouderd zijn en welke niet. Een beoordeling met een verouderde afhankelijkheid krijgt `stale = true` en wordt nooit stilzwijgend herrekend.

`kernel_rule` hoort in deze opsomming omdat kernregels versioneerde records zijn waar een oordeel werkelijk van afhangt. Ze zijn onveranderlijk in de zin dat de applicatie ze niet kan wijzigen of verwijderen, maar de kernset kan bij een herziening van dit document veranderen — dat is in dit project ook gebeurd. Zonder deze soort blijft zo'n wijziging onzichtbaar in het register.

**Afgeleide overzichten** (views, geen aparte opslag): regels die de toets hebben doorstaan en actief zijn; regels die zijn afgevallen met reden en aanleiding; regels die op elkaar steunen; beoordelingen die verouderd zijn door een recente wijziging.

### 5.13 Corpus — leeg in dit bouwplan

Nodig voor functies 3 en 4 (§4.4). In fase 1 worden de tabellen aangemaakt en blijven ze leeg; er wordt geen code voor geschreven. Ze staan hier zodat het schema later geen migratie nodig heeft.

**`corpus_source`** — een brontekst of verzameling (bv. een hadithcollectie, een fatwaverzameling, een werk van een geleerde), met `name`, `kind`, `license`, `access_method`.

**`corpus_entry`** — een adresseerbare eenheid binnen een bron (vers, hadith, passage), met `source_ref`, `locator`, `text`, `language`.

**`retrieval_session`** — `mode` (attack | defend), `claim_ref`, `corpus_scope[]`, `query`, `executed_at`, `found[]` (verwijzingen naar corpus_entry), `not_found_note`. Hiermee verschilt "geen sterke aanval gevonden" aantoonbaar van "niet gezocht", zoals §4.4 eist.

---

## 6. De motor — wat hij moet doen

Voor één claim onder één profiel en één competentieniveau, in de volgorde van B2:

1. **Ontleden.** Splits de tekst in atomaire claims. Per claim: premissen, bronnen, inferentiestappen. (LLM-voorstel → bevestigingspoorten per B4.)
2. **Verzwegen premissen.** Stel kandidaat-premissen voor die de keten sluitend maken. Toon ze als expliciete, bevestigbare aannames. Presenteer nooit een reconstructie als zeker.
3. **Thubut.** Roep per premisse het instrument aan dat bij het type hoort. Sla de gestandaardiseerde uitvoer op. Recursief bij sub-premissen.
4. **Status.** Bepaal per tekst de status (bv. muhkam/mutashabih, nasikh/mansukh). Status is een **afgeleid oordeel** uit eigen toetsen — naskh bijvoorbeeld uit zes voorwaarden — en nooit een kale vlag. Elke statustoets is zelf een beoordeelbare claim.
5. **Dalalah.** Per tekstpremisse: welke interpretatie wordt gebruikt, wat zijn haar gronden, wat is haar sterkte. Zonder `interpretation_ref`: stop.
6. **Inferentie.** Per stap: schema vaststellen, kritische vragen stellen, elke gefaalde of onbeantwoorde vraag registreren als undercut of undermine.
7. **Drogredenen.** Scan op structurele drogredenen. Merk op dat veel informele drogredenen samenvallen met een schema waarvan de kritische vragen falen; dubbel tellen is verboden.
8. **Reikwijdte en conflict.** Bij conflicterende premissen of regels: vergelijk eerst reikwijdte. Disjunct → geen conflict. Overlap → conflict beperkt tot het snijvlak → conflictvolgorde uit het profiel (bv. jam' → naskh → tarjih → tawaqquf), met **terminologische ontwarring** als eerste toets: gebruiken beide bronnen de term in dezelfde betekenis?
9. **Aanvallen.** Bouw de nederlaaggraaf (B3), draai grounded semantics, zet statussen.
10. **Zekerheid.** Conclusie = zwakste schakel (min) over de keten. Convergente onafhankelijke steun mag het label verhogen (noisy-OR), mits de onafhankelijkheid is vastgesteld. Domeindrempel uit het profiel plafonneert het eindlabel.
11. **Kantelpunten.** Bepaal welke premisse, interpretatie of kritische vraag, indien gewijzigd, het eindlabel doet kantelen.
12. **Rapporteren.** Alle assen, zwakste schakel, open vragen, kantelpunten, en de volledige keten uitklapbaar tot de bron. Nooit één getal.

Voor een **vergelijking**: draai stap 1–12 per claim, bepaal gedeelde premissen, lokaliseer het kleinste punt van uiteengaan, en vul `comparison` (§5.10).

---

## 7. Instrumenten (plugins) — interface

Elk instrument neemt een premisse en levert:

```
{
  premise_id,
  instrument,
  thubut:   {label, rationale},
  dalalah:  {label, rationale}   // optioneel; sommige instrumenten meten alleen thubut
  confidence,
  flags[],
  subgraph  // optioneel: sub-premissen die de motor opnieuw doorrekent
}
```

De motor gebruikt uitsluitend `thubut`, `dalalah`, `confidence`, `flags` en `subgraph`. Al het andere is intern voor het instrument.

Eerste instrumenten (fase 3): een isnad-instrument dat bestaande hadith-API's raadpleegt en meerdere gradingen naast elkaar teruggeeft (nooit één "de" grading), en een eenvoudig risk-of-bias-instrument voor empirische studies. Beide zijn bewust minimaal.

---

## 8. Tests — twee soorten, strikt gescheiden

**Kalibratietests.** Gevallen waarover niemand voor wie het instrument bedoeld is van mening verschilt, met bekend antwoord. Bijvoorbeeld "het gebed is verplicht" met zijn bronnen: moet bovenaan de schaal landen. Bron: de aqeedah-grondslagentekst. Alleen hier is een vooraf bekend antwoord legitiem.

**Eigenschapstests.** Betwiste gevallen, **zonder** bekend antwoord. Hier wordt nooit de conclusie getoetst, uitsluitend:
- *Structuur*: is de tekst opgedeeld in aparte claims; is een punt van uiteengaan gevonden.
- *Tekstuele feiten*: beweert de motor iets over een tekst dat aantoonbaar niet in de tekst staat.
- *Symmetrie*: dezelfde argumentvorm krijgt aan beide kanten hetzelfde label.
- *Invariantie*: wissel de etiketten van de partijen; de scores mogen niet veranderen. Wissel de invoervolgorde; idem.
- *Eerlijkheid van weergave*: de reconstructie moet door beide partijen als eerlijke weergave van hun eigen argument herkend worden (Rapoport-toets). Dit is een menselijke controle, geen automatische.

Een afwijking tussen motoruitkomst en een eerdere handmatige analyse is een **te onderzoeken verschil**, geen bug. Het kan beide kanten op.

---

## 9. Waarborgen (harde filters, niet omzeilbaar)

- Het systeem doet nooit een uitspraak over het geloof, de oprechtheid, de kufr of de iman van een persoon of groep. Een aparte classifier detecteert dergelijke input, blokkeert elk waarde-oordeel, toont hooguit de methodologische landschapschets van geleerde posities, en escaleert naar menselijke review.
- Het systeem scoort claims, nooit personen. Geen ranglijsten van personen.
- Elke beoordeling toont expliciet dat hij door een AI-systeem is gegenereerd (AI Act, art. 50) en welke profielversie is gebruikt.
- Gebruikersinhoud: notice-and-action-mechanisme en klachtenprocedure (DSA).
- Persoonsgegevens: minimaal; menselijke review op verzoek; geen geautomatiseerde besluiten met rechtsgevolg (AVG art. 22).
- De framing in elke schermtekst: het instrument beoordeelt methodologie en bewijskracht, niet waarheid.

---

## 10. Wat NIET bouwen

- Geen eigen hadith-database. Integreer bestaande bronnen via hun API's; respecteer hun licenties.
- Geen fatwa-functie. Het systeem geeft geen oordelen, het beoordeelt oordelen.
- Geen enkel eindcijfer, ook niet "voor het gemak" in een dashboard.
- Geen hardgecodeerde islamitische regel, ook niet "tijdelijk".
- Geen steelmanning als standaard; alleen als expliciete optie.
- Geen automatische vergelijking van personen of scholen; alleen van ingediende claims.
- Geen volledig uitgewerkt UI-ontwerp vóór fase 6.
- Geen containerisatie vóór fase 3, en dan uitsluitend één image voor de motor. Geen compose-opstelling, geen aparte database- of API-container vóór fase 6.

---

## 11. Gefaseerd bouwplan

Elke fase levert iets dat draait en te testen is. Ga niet naar de volgende fase voordat alle acceptatiecriteria aantoonbaar zijn gehaald.

### Fase 1 — Datamodel, kern en nultest

**Bouwen.** Het datamodel uit §5 (alle tabellen, ook die pas later gevuld worden — inclusief het register uit §5.12 en de lege corpustabellen uit §5.13). De kernregels als records. De motor met uitsluitend de kern: stappen 1, 2, 6 (alleen structurele en formele toetsen), 7 (alleen formele drogredenen), 10, 11, 12. Een minimale invoer via bestand of API; nog geen UI, nog geen LLM. Invoer is handmatig gestructureerde JSON.

Twee eisen die de omgeving betreffen en nu goedkoop zijn:

- **Afhankelijkheden hard vastpinnen.** Exacte versies plus een lockfile. Dit is geen stijlvoorkeur maar volgt uit de reproduceerbaarheidseis: een beoordeling moet later te herhalen zijn, en een gewijzigde bibliotheek kan bij dezelfde invoer een andere uitkomst geven.
- **Configuratie buiten de code.** Databasepad, seed-map en uitvoermap als omgevingsvariabelen met een zinnige standaardwaarde. Geen paden hardgecodeerd.

**Nultest.** Met **nul qawa'id geladen** en een leeg profiel moet de motor:
1. zonder fout draaien;
2. een handmatig gestructureerde invoer ontleden in claims, premissen en inferenties;
3. een verzwegen premisse melden waar een inferentie niet sluit;
4. de zwakste schakel correct aanwijzen;
5. formele drogredenen (bevestigen van het consequens, ontkennen van het antecedent, onverdeelde middenterm, cirkelredenering) herkennen;
6. "onvoldoende bewijs" teruggeven als een premisse geen bron heeft;
7. **weigeren** een enkel getal te produceren (API-contract test).

Doel van de nultest: bewijzen dat er niets inhoudelijks in de code zit. Faalt een van deze zeven zonder regels, dan zit de fout in de kern en wordt hij daar gerepareerd.

**Kalibratie.** De aqeedah-grondslagentekst als handmatig gestructureerde invoer: "het gebed is verplicht" met zijn bronnen. Verwacht: hoogste label. Faalt dit, stop en repareer.

**Acceptatie.** Alle zeven nultest-criteria groen. Kalibratie groen. Elk score-object bevat `rationale`. Geen enum voor inhoudelijke velden. Versienummers aanwezig. Elke premisse heeft een expliciete `provenance`. Een tweede beoordeling van dezelfde claim maakt een nieuwe rij met `supersedes` gevuld en overschrijft niets. `assessment_dependency` wordt gevuld bij elke beoordeling. De corpustabellen bestaan en zijn leeg.

### Fase 2 — Profielen en regels

**Bouwen.** `profile`, `qaida`, `edge`, cascade (`effective_strength`), cykeldetectie, `conflicts_with_kernel`, `not_independently_decidable`, laadvalidatie van plafonds, aanvalsemantiek (B3) met bibliotheek.

**Vullen.** Vijftien tot twintig qawa'id, door de opdrachtgever aangeleverd, bewust gekozen zodat ze samen elk veld belasten: elke waarde van `function`; een keten van drie diep in `depends_on`; één bewust circulair paar; minstens één regel per domein (usul, tafsir, aqeedah, bid'ah, finance); één regel die een andere aanvalt; één regel met zwak bewijs. Twee profielen: een dat de regels van de anti-taqleed-boeken bundelt en een dat de hanafitische positie bundelt.

**Acceptatie.** Elke aangeleverde qaida is zonder schemawijziging op te slaan (lukt dat niet, dan is dat de bevinding en wordt het schema nu aangepast). Cascade werkt: verzwak een wortelregel en zie de kinderen meezakken. Het circulaire paar wordt gedetecteerd en gemeld, niet berekend. Een qaida die een kernregel tegenspreekt krijgt `conflicts_with_kernel` en wordt getoond, niet genegeerd. Wederzijdse aanval bij gelijk label → beide `undecided`; bij ongelijk label → de sterkere wint. Laden van een profiel met een type zonder plafond faalt met een duidelijke melding.

### Fase 3 — Bronnen en instrumenten

**Bouwen.** `premise_type` als profieltabel, `type_ceilings`, plugin-interface (§7), recursieve premissen (`sub_premises`), citaatintegriteit (`verification_status`). Twee instrumenten: isnad (via bestaande API's, meerdere gradingen naast elkaar) en risk-of-bias (minimaal).

**Containerisatie.** Vanaf deze fase, niet eerder. Reden: zodra externe API's en instrumenten meedoen, is de omgeving zelf onderdeel van de uitkomst. De reproduceerbaarheidseis vraagt dat een beoordeling later te herhalen is; `engine_version` alleen volstaat dan niet, want een gewijzigde bibliotheek kan bij dezelfde invoer een ander antwoord geven. Leg daarom de image-hash vast bij elke beoordeling, naast `engine_version`, `profile_version` en `ruleset_version`.

Bouw uitsluitend wat deze fase nodig heeft: één image voor de motor. Geen compose-opstelling, geen databasecontainer, geen API-container. Die horen bij fase 6 en vallen tot dan onder §10.

**Acceptatie.** Een ijmaa'-claim laat zich opslaan als premisse met sub-premissen (dat er consensus was; hoe die is overgeleverd; of er een grondslag onder ligt), en de motor rekent de zwakste sub-premisse door naar het geheel. Een instrument dat een deelgraaf teruggeeft wordt correct opnieuw doorgerekend. Een citaat met `verification_status = disputed` verlaagt de thubut-score en wordt in de rapportage genoemd. Het plafond van een type wordt nooit overschreden. De motor draait in een container, elke beoordeling legt de image-hash vast, en dezelfde invoer levert in twee verse containers een identieke uitkomst.

### Fase 4 — Interpretatie en status

**Bouwen.** `interpretation` met gronden en `supporters` (niet-scorend), de verplichte `interpretation_ref` op inferenties, statusvelden met `opposition`, naskh als afgeleid oordeel uit zes toetsen (bestaan van nasikh; afgeschafte is een shar'i oordeel; afschaffende is shar'i bewijs; later en losstaand; niet zwakker; werkelijk onverzoenbaar), de vaste evaluatievolgorde (B2) afgedwongen in code, reikwijdtevergelijking en conflictmodule met terminologische ontwarring als eerste toets, `figurative_reading_permitted`.

**Acceptatie.** Een inferentie van tekst naar conclusie zonder `interpretation_ref` wordt geweigerd met melding. Twee interpretaties van hetzelfde vers zijn naast elkaar op te slaan en apart te scoren; de aanhangers tellen niet mee. Een naskh-claim zonder aangewezen nasikh wordt afgewezen. Een naskh-claim waarbij de nasikh zwakker is dan de mansukh slaagt niet. Twee regels met disjuncte reikwijdte melden geen conflict; twee met overlap wel, beperkt tot het snijvlak. Bij een profiel met `figurative_reading_permitted = false` wordt geen figuurlijke lezing als kandidaat opgevoerd. Statuslabel `muhkam` zonder `opposition` wordt geweigerd.

### Fase 5 — AI-invoer

**Bouwen.** LLM-stap die vrije tekst omzet in voorstellen voor claims, premissen, typen, schema's en verzwegen premissen, elk met confidence. Bevestigingspoorten (B4). Opslag als `proposed` tot bevestiging. Meertalig (NL/EN/AR, met Pashto en Urdu als latere uitbreiding); RTL-ondersteuning in de opslag en API.

**Acceptatie.** Een geplakte tekst levert voorstellen op die de motor pas verwerkt na bevestiging van type en schema. Een voorstel onder de drempel wordt altijd ter bevestiging aangeboden. Eigenschapstest symmetrie: dezelfde alinea, aangeboden als afkomstig van partij A en van partij B, levert identieke structuurvoorstellen. LLM-versie wordt vastgelegd bij elk voorstel.

### Fase 6 — Vergelijking, UI en compliance

**Bouwen.** Het `comparison`-object en de deltaweergave. Web-UI en app: invoer, resultaat (alle assen, uitklapbaar tot de bron), vergelijking. AI-disclosure, notice-and-action, klachtenprocedure, takfir-filter (§9).

**Eerste echte eigenschapstest.** De taqleed-discussie: de argumenten van beide kanten ingevoerd, onder beide profielen uit fase 2. Getoetst wordt **uitsluitend**: is de tekst in aparte claims opgedeeld; is een punt van uiteengaan gelokaliseerd; klopt wat de motor over de teksten zelf beweert (bv. dat 16:43 "vraag" zegt en niet "volg"); krijgt dezelfde argumentvorm aan beide kanten hetzelfde label; en herkennen lezers van beide kanten hun eigen argument in de reconstructie. De conclusie wordt **niet** getoetst. Een afwijking van de eerdere handmatige analyse is een te onderzoeken verschil.

**Acceptatie.** Alle eigenschapstests uit §8 groen op de taqleed-casus. Geen enkel scherm toont één getal. Elke beoordeling toont de AI-disclosure en de profielversie. Het takfir-filter blokkeert een testinvoer die om een oordeel over een persoon vraagt.

---

## 12. Open items (blokkeren niet, wel plannen)

- Drie dragende citaten in de testset zijn nog niet in de bronnen geverifieerd; de opdrachtgever levert ze vóór fase 6.
- De definitieve naam.
- Scholarly advisory board vóór publieke lancering (buiten scope van de bouw, wel voorwaarde voor livegang).
