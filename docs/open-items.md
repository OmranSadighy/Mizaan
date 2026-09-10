# Open items

Dingen die nu bewust niet zijn gebouwd en die in een latere fase alsnog moeten
gebeuren. Ze blokkeren fase 1 niet, maar mogen niet vergeten worden.

## Voor fase 2

**De interim-regels van §4.5 vervallen.** De gefaalde kritische vraag wordt
vervangen door de nederlaaggraaf uit B3; de convergentieregel wordt vervangen
zodra de afbeelding van labels op kansen als qaida bestaat. Elk rapport noemt
onder `interim_regels` welke regel wanneer vervalt.

**`stale` wordt gezet.** De kolom en het overzicht
`v_verouderde_beoordelingen` bestaan en werken, maar in fase 1 verandert er
niets waardoor een beoordeling verouderen kan: er zijn geen qawa'id. Zodra die
er zijn, moet de motor de vlag zetten wanneer een afhankelijkheid verandert, en
de beoordeling nooit stilzwijgend herrekenen.

## Voor fase 3

**De domeindrempel moet werkelijk aftoppen.** §6 stap 10 zegt dat de
domeindrempel uit het profiel het eindlabel plafonneert. Fase 1 bouwt dat niet:
zonder geladen plafonds zou het dode code zijn, en dode code is erger dan geen
code. Het schema draagt de plafonds al (`profile_premise_type.ceiling_label`).

Wat er in fase 3 moet komen:

* toepassing van het plafond per premissetype, en van het eindlabel;
* de laadvalidatie uit §5.2 die een type zonder plafond tot laadfout maakt
  (fase 2);
* **een test die aantoont dat een plafond werkelijk aftopt**: een keten waarvan
  elke schakel `certain` is, met een profiel dat het gebruikte type op `probable`
  plafonneert, moet `probable` opleveren en niet `certain`. Een plafond dat
  nooit ergens op bijt, is opnieuw dode code.

**Containerisatie.** Vanaf fase 3, één image voor de motor, en de image-hash
wordt bij elke beoordeling vastgelegd naast de motor-, profiel- en
regelsetversie. Niet eerder, en geen compose-opstelling.

## Voor de fase waarin aanvallen en verdedigen komen

**Onderscheid tussen "zwak aangeleverd" en "zwak na zoeken".** §4.4 eist dat de
uitvoer verschil maakt tussen "dit aangeleverde argument steunt X zwak" en "de
sterkste onderbouwing die ik voor X kan vinden is zwak". Het eerste zegt de motor
nu al. Het tweede vraagt een veld op de beoordeling dat zegt of er gezocht is, en
zo ja met welke zoeksessie. `retrieval_session` draagt de zoektocht al; de
verwijzing vanaf de beoordeling ontbreekt nog, omdat er nog niet gezocht wordt.

## Uit §12 van de bouwspecificatie

* Drie dragende citaten in de testset zijn nog niet in de bronnen geverifieerd;
  de opdrachtgever levert ze vóór fase 6.
* De definitieve naam.
* Scholarly advisory board vóór publieke lancering.
