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
distributieregels. De structuurtoets gaat verder dan het tellen van drie
verschillende termen: elke conclusieterm moet in precies één premisse staan en
de middenterm in beide. Zonder die eis laat de toets een conclusie door met een
term waar de premissen niets over zeggen, en dat is zekerheid uit niets. De toets
levert precies de vijftien stemmingen op die onder de moderne lezing geldig zijn;
`tests/test_eigenschappen.py` rekent dat na.

Een stap met meer of minder dan twee categorische premissen heet **niet
toetsbaar**, niet ongeldig. Een sluitende sorites van drie premissen is geldig,
maar niet met deze toets vast te stellen, en de motor bewijst geen gat.

Propositionele stappen worden getoetst met een volledige waarderingstabel, niet
met patroonherkenning; patroonherkenning dient alleen om een gevonden
ongeldigheid bij naam te noemen, en één stap krijgt hooguit één naam. Dubbele
ontkenningen worden bij het normaliseren weggewerkt, anders herkent de motor de
benoemde drogredenen niet meer.

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
  dezelfde tekortkoming niet twee keer gemeld wordt en zodat zij niet losgaat op
  een stap die formeel sluit.

De zoektocht naar vormaanvullingen is begrensd. Boven een bepaald aantal losse
termen wordt zij overgeslagen, en dat staat in de rationale. Een lege lijst
kandidaten betekent daar dus niet "er is niets gevonden".

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
zichzelf uit, via premissen die een andere claim beweren.

De graaftoets gebruikt sterk samenhangende componenten (Tarjan). Een eenvoudige
diepteweergave met een "al bezocht"-markering is niet genoeg: die vindt per
zoektocht wel een kring, maar mist knopen die alleen via een al afgeronde tak in
een kring liggen. Voor deze motor is dat geen detail, want een gemiste kring
betekent dat een claim die op zichzelf steunt een positief label krijgt.

Steunkringen zijn een eigenschap van de ontleding, niet van de
zekerheidsberekening. Ze worden in stap 1 bepaald, zodat stap 7 ze kan gebruiken
zonder de uitkomst van stap 10 te raadplegen (B2). Claims in een steunkring
worden niet doorgerekend; ze krijgen `undetermined` en `insufficient_evidence`,
en elke claim in de kring meldt dat in haar eigen rapport. Een claim die op een
kring steunt, ziet die kring onder `steunkring.kringen_in_de_keten`.

## 13. Herleidbaarheid naar de kernregel

Elke bevinding noemt de kernregel waarop zij steunt, en die koppeling staat in de
lookup-tabel, niet in code. Elk rapport draagt de tekst van de toegepaste
kernregels mee, met hun zelfvernietigingsargument. Zo is niet alleen het argument
van de auteur uitklapbaar tot de bron, maar ook het redeneren van de motor zelf.

## 14. Versies

Elke beoordeling draagt vijf versies: motor, contract, invoerschema, profiel en
regelset. De regelsetversie is een sha256-vingerafdruk, als tekst.

Zij dekt niet alleen de kernregels en de qawa'id maar ook de lookup-rijen voor
zover die het rekenen sturen (de rangorde van de sterkteschaal, de koppeling van
een bevindingssoort aan haar kernregel, of een rij actief is) en de sjablonen van
de kritische vragen. Dat moet zo: omdat regels data zijn, beweegt het oordeel mee
met een gewijzigde rij, en een vingerafdruk die zo'n wijziging niet ziet maakt de
beoordeling onreproduceerbaar. Een gewijzigde vertaling van een label stuurt het
oordeel niet en raakt de vingerafdruk dus ook niet.

## 15. De kern is dragend

De motor weigert te rekenen als een van de vijf kernregelrecords ontbreekt. Zij
kiest ook zelf geen kernregel wanneer de lookup er niet een noemt bij een soort
bevinding: dat is een gat in de data en geen reden om er in code een te kiezen.
Zonder deze twee zou de bewering dat de kern expliciet en dragend is, niet
kloppen: de motor zou precies hetzelfde rekenen met een lege kerntabel.

## 16. Weigeren in plaats van stil laten vallen

Fase 1 kent velden die het schema draagt maar de motor nog niet verwerkt. Ze
worden geweigerd met uitleg, niet aangenomen en weggegooid. Dat geldt voor de
gebruiksvormen vergelijken, aanvallen en verdedigen, voor een `interpretation_ref`
op een inferentie, voor een verwijzing naar een corpusdocument, voor qawa'id in
een profiel, en voor een competentieniveau dat het profiel niet kent. Stil
weggooien is erger dan weigeren: de indiener denkt dan dat zijn gegeven is
meegewogen.

Ondoorzichtige lading van de indiener, zoals `provenance.detail` en
`instrument_output`, gaat wél mee. Zij reist als JSON-tekst door de rapportage,
zodat zij bewaard blijft zonder dat er een getal in de uitvoer belandt.
