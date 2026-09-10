# Conventies en keuzes in fase 1

Dit document legt de keuzes vast die het oordeel beïnvloeden en die niet
letterlijk in de bouwspecificatie staan. Ze staan hier zodat ze te betwisten
zijn. Een keuze die alleen in de code staat, is geen keuze maar een aanname.

## 1. De sterkteschaal is data

`certain > strong > probable > weak > undetermined` staat als vijf rijen in
`lu_strength_label`, met een `rangorde` die de ordening bepaalt. De rangorde is
intern: zij bepaalt wat minimum en maximum betekenen en verlaat de motor nooit
als uitvoer. Een trede toevoegen of de ordening veranderen kan zonder
codewijziging; `tests/test_regels_zijn_data.py` bewijst dat.

`undetermined` is niet "de laagste sterkte" maar "niet vastgesteld". Bij de
zwakste-schakelregel gedraagt het zich als laagste waarde, want onbekende
sterkte levert geen sterkte. Dat is een keuze, geen logische noodzaak.

## 2. Minimum binnen een lijn, maximum over lijnen

Binnen één bewijslijn geldt het minimum over premissen en redeneerstap. Dat is
de kernregel `zwakste_schakel`.

Over bewijslijnen heen geldt het maximum. Een claim met één sluitende
bewijslijn en daarnaast een slechte lijn is door die slechte lijn niet zwakker
geworden. De reden staat in elke rationale.

Fase 1 verhoogt het label **niet** bij convergente onafhankelijke steun. Dat zou
een afbeelding van labels op kansen vragen, en die afbeelding is een instelbare
regel met eigen bewijs, geen kernregel. Zij komt met noisy-OR in een latere
fase, als qaida met een eigen record, en de getallen verlaten de motor nooit.

## 3. Moderne lezing zonder existentiële import

`alle S zijn P` zegt niet dat er S bestaat. Daaruit volgt dat uit twee
universele premissen geen particuliere conclusie volgt: Darapti, Felapton,
Bramantip en Fesapo gelden hier als ongeldig.

De vier drogredenen die de nultest vraagt zijn ongevoelig voor deze keuze.
Andere gevallen niet. Wie de klassieke lezing mét existentiële import wil, moet
dat als expliciete regel toevoegen; hij zit niet stilzwijgend in de motor.

De geldigheid van categorische syllogismen wordt bepaald met de klassieke
distributieregels: drie termen, middenterm minstens één keer gedistribueerd,
geen term gedistribueerd in de conclusie die dat niet is in zijn premisse, niet
twee ontkennende premissen, en ontkennende premisse precies dan als de conclusie
ontkennend is. Propositionele stappen worden getoetst met een volledige
waarderingstabel, niet met patroonherkenning; patroonherkenning dient alleen om
een gevonden ongeldigheid bij naam te noemen.

## 4. Onverenigbare premissen maken een stap niet geldig

Klassiek volgt uit een tegenstrijdige premissenverzameling alles. Zou de motor
dat als geldig rapporteren, dan liet zij zekerheid ontstaan uit een tegenspraak.
De motor meldt in dat geval `contradictory_premises` en noemt de vorm ongeldig.
Dit steunt op `non_contradictie` en `zwakste_schakel`.

## 5. De motor bewijst geen gat

Een mogelijk verzwegen premisse heet altijd "mogelijk verzwegen premisse", nooit
een vaststelling dat er iets ontbreekt. De rationale noemt de gebruikte toets.
Er zijn er twee:

* **Vormaanvulling.** De aangeleverde premissen leveren de conclusie formeel
  niet op. De motor zoekt de logisch zwakste aannames die de stap wél sluitend
  maken, laat aannames weg die de premissen tegenspreken, en laat aannames weg
  die de conclusie in hun eentje al opleveren. Dat laatste sluit "neem de
  conclusie maar aan" uit. Van logisch gelijkwaardige kandidaten blijft er één
  over.
* **Termdekking.** Een term uit de conclusie komt in geen enkele premisse voor.
  Dit is nadrukkelijk een heuristiek: de verbinding kan ook in de woorden zelf
  besloten liggen. De toets draait alleen als de vorm niet toetsbaar is, zodat
  dezelfde tekortkoming niet twee keer gemeld wordt.

Een voorstel krijgt `proposed_by = engine` en `confirmed = false`, en telt niet
mee in de sterkte tot het bevestigd en van een bron voorzien is.

## 6. Kritische vragen en dubbel tellen

De basisvragen per argumentatieschema staan als data in
`scheme_critical_question`. Een profiel kan de vragenset van een schema
uitbreiden; zulke rijen dragen `origin = profile` en verwijzen naar de qaida die
ze toevoegt. Basisvragen dragen `origin = base`.

Een vraag kan een motorcapaciteit noemen in `beantwoordbaar_door_motor`. De
enige capaciteit in fase 1 is `form_validity`. Beantwoordt de motor een vraag
zelf, dan levert die vraag **geen** apart effect op het label: het effect zit al
in de uitkomst van de toets waarmee zij beantwoord is. Zo is dubbel tellen
uitgesloten (§6 stap 7). Geeft de invoer voor zo'n vraag een andere status op,
dan gaat de formele toets voor en staat dat in de toelichting.

## 7. Interim-regel: een gefaalde kritische vraag plafonneert op onbepaald

Een **onbeantwoorde** kritische vraag verlaagt niets; zij wordt gemeld als
openstaand en verschijnt als kantelpunt. Een vraag met status **gefaald** zet het
label van de stap op onbepaald. Anders zou de motor een stap sterk noemen die zij
zelf als gebroken heeft gemarkeerd, en dat is tegenstrijdige uitvoer.

Dit is een interim-regel voor fase 1. In fase 2 neemt de nederlaaggraaf met
grounded semantics deze rol over, en dan zijn status en sterkte weer volledig
gescheiden assen zoals B3 voorschrijft.

## 8. Een formele toets gaat voor een aangeleverd label

Levert de invoer een sterkte aan voor een stap die formeel geldig of ongeldig
blijkt, dan wint de formele uitkomst. De geldigheid van een vorm is een
vaststelling, geen inschatting. De rationale meldt welk label is overruled.

## 9. Een premisse zonder bron

Een premisse heeft steun als zij een `citation.source_ref` noemt, sub-premissen
heeft, of een andere claim beweert. Ontbreekt alle drie, dan is haar sterkte
onbepaald, wordt een aangeleverde score **genegeerd en gemeld**, en verschijnt
zij in `insufficient_evidence.premissen_zonder_bron`.

`insufficient_evidence` staat op waar wanneer elke bewijslijn van de claim zo'n
premisse bevat, of wanneer de claim geen enkele bewijslijn heeft. Raakt het maar
een deel van de lijnen, dan staat het op onwaar en noemt de uitleg welke lijnen
niet dragen.

## 10. Recursie over sub-premissen

De zwakste-schakelregel werkt ook binnen een premisse: een premisse met
sub-premissen is niet sterker dan haar zwakste sub-premisse. Dat is een directe
toepassing van een kernregel op de structuur die §5.6 voorschrijft, en bevat
geen inhoudelijke kennis.

Wat fase 3 toevoegt is niet de recursie maar het instrument dat sub-premissen
meet en een deelgraaf kan teruggeven, plus de plafonds per premissetype.

## 11. Kantelpunten in twee richtingen

Voor elk element wordt de hele berekening opnieuw gedraaid met precies één
gewijzigde waarde. Gerapporteerd wordt de **kleinste** wijziging die het
eindlabel doet kantelen, omhoog én omlaag. Er wordt niets benaderd.

Voor een stap waarvan de vorm bewezen geldig is, wordt geen kantelpunt gemeld:
een andere waarde zou geen wijziging zijn die iemand kan aanleveren, maar de
ontkenning van een vaststelling. Voor een premisse zonder bron is het kantelpunt
"een bron aanleveren", met het label dat daaruit zou volgen.

## 12. Cirkelredenering

Twee toetsen. Op vormniveau: de conclusie komt letterlijk als premisse voor. Op
graafniveau: de steun voor een claim komt langs haar eigen premissen weer bij
zichzelf uit, via premissen die een andere claim beweren. Claims in een
steunkring worden niet doorgerekend; ze krijgen `undetermined` en
`insufficient_evidence`, en elke claim in de kring meldt dat in haar eigen
rapport.

## 13. Herleidbaarheid naar de kernregel

Elke bevinding noemt de kernregel waarop zij steunt, en die koppeling staat in de
lookup-tabel, niet in code. Elk rapport draagt de tekst van de toegepaste
kernregels mee, met hun zelfvernietigingsargument. Zo is niet alleen het argument
van de auteur uitklapbaar tot de bron, maar ook het redeneren van de motor zelf.

## 14. Versies

Elke beoordeling draagt vijf versies: motor, contract, invoerschema, profiel en
regelset. De regelsetversie is een sha256-vingerafdruk over de kernregels en de
qawa'id, als tekst. Zij verandert zodra een regel verandert, zodat een
beoordeling reproduceerbaar aan haar regelset hangt.
