"""Logische vormen en hun formele toetsing.

Deze module kent geen enkel onderwerp. Zij kent alleen vorm, en steunt daarmee
op de kernregel ``vorm_versus_waarheid``: geldigheid van de vorm en waarheid van
de premissen zijn onderscheiden.

Ondersteunde vormen (lookup ``form_kind``):

* ``atomic``       ``{"kind": "atomic", "term": "t"}``
* ``negation``     ``{"kind": "negation", "of": <vorm>}``
* ``conditional``  ``{"kind": "conditional", "antecedent": <vorm>, "consequent": <vorm>}``
* ``categorical``  ``{"kind": "categorical", "quantity": "all"|"no"|"some"|"some_not",
                      "subject": "S", "predicate": "P"}``

Conventies, vastgelegd omdat zij het oordeel beïnvloeden:

1. **Moderne lezing zonder existentiële import.** ``alle S zijn P`` zegt niet dat
   er S bestaat. Daaruit volgt dat uit twee universele premissen geen
   particuliere conclusie volgt. De vier drogredenen die de nultest vraagt zijn
   ongevoelig voor deze keuze; andere gevallen niet, en daarom staat de keuze
   hier en niet impliciet in de code.
2. **Onverenigbare premissen maken een stap niet geldig.** Klassiek volgt uit
   een tegenstrijdige premissenverzameling alles. Zou de motor dat als geldig
   rapporteren, dan zou zij zekerheid uit een tegenspraak laten ontstaan. De
   motor meldt in dat geval de tegenspraak en noemt de vorm ongeldig. Dit steunt
   op ``non_contradictie`` en ``zwakste_schakel``.
3. **De motor bewijst geen gat.** Slaagt een formele toets niet, dan zegt de
   motor wat zij heeft getoetst en wat daaruit volgt, nooit dat er zeker iets
   ontbreekt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any

PROPOSITIONEEL = ("atomic", "negation", "conditional")
MAX_ATOMEN = 14
# De zoektocht naar mogelijk verzwegen premissen is duurder dan de vormtoets:
# zij bouwt kandidaten over alle termen en vergelijkt ze onderling. Boven deze
# grens wordt zij overgeslagen, en dat wordt gemeld in plaats van stilzwijgend
# als "geen kandidaten gevonden" gerapporteerd.
MAX_ATOMEN_KANDIDATEN = 10

NEGATIEVE_KWANTITEITEN = frozenset({"no", "some_not"})
PARTICULIERE_KWANTITEITEN = frozenset({"some", "some_not"})


class VormFout(ValueError):
    """De aangeleverde vorm is niet leesbaar."""


# --------------------------------------------------------------------------
# Normaliseren en weergeven
# --------------------------------------------------------------------------


def normaliseer(vorm: Any) -> dict[str, Any]:
    """Breng een vorm in canonieke gedaante. Een kale tekst wordt atomair."""
    if isinstance(vorm, str):
        return {"kind": "atomic", "term": vorm}
    if not isinstance(vorm, dict) or "kind" not in vorm:
        raise VormFout(f"onleesbare vorm: {vorm!r}")
    soort = vorm["kind"]
    if soort == "atomic":
        term = vorm.get("term")
        if not isinstance(term, str) or not term.strip():
            raise VormFout("een atomaire vorm heeft een niet-lege 'term' nodig")
        return {"kind": "atomic", "term": term.strip()}
    if soort == "negation":
        if "of" not in vorm:
            raise VormFout("een ontkenning heeft 'of' nodig")
        binnenste = normaliseer(vorm["of"])
        # Een dubbele ontkenning valt weg. Zonder deze stap zou 'niet niet p'
        # als een andere propositie gelden dan 'p', en dan herkent de motor
        # bijvoorbeeld het ontkennen van het antecedent niet meer.
        if binnenste["kind"] == "negation":
            return binnenste["of"]
        return {"kind": "negation", "of": binnenste}
    if soort == "conditional":
        if "antecedent" not in vorm or "consequent" not in vorm:
            raise VormFout("een voorwaardelijke vorm heeft 'antecedent' en 'consequent' nodig")
        return {
            "kind": "conditional",
            "antecedent": normaliseer(vorm["antecedent"]),
            "consequent": normaliseer(vorm["consequent"]),
        }
    if soort == "categorical":
        kwantiteit = vorm.get("quantity")
        onderwerp = vorm.get("subject")
        gezegde = vorm.get("predicate")
        if kwantiteit not in {"all", "no", "some", "some_not"}:
            raise VormFout(f"onbekende kwantiteit: {kwantiteit!r}")
        if not isinstance(onderwerp, str) or not isinstance(gezegde, str):
            raise VormFout("een categorische vorm heeft 'subject' en 'predicate' nodig")
        return {
            "kind": "categorical",
            "quantity": kwantiteit,
            "subject": onderwerp.strip(),
            "predicate": gezegde.strip(),
        }
    raise VormFout(f"onbekende vormsoort: {soort!r}")


def weergave(vorm: dict[str, Any]) -> str:
    """Nederlandse weergave van een vorm, voor de rapportage."""
    soort = vorm["kind"]
    if soort == "atomic":
        return vorm["term"]
    if soort == "negation":
        return f"niet ({weergave(vorm['of'])})"
    if soort == "conditional":
        return f"als {weergave(vorm['antecedent'])}, dan {weergave(vorm['consequent'])}"
    if soort == "categorical":
        sjabloon = {
            "all": "alle {s} zijn {p}",
            "no": "geen {s} is {p}",
            "some": "sommige {s} zijn {p}",
            "some_not": "sommige {s} zijn niet {p}",
        }[vorm["quantity"]]
        return sjabloon.format(s=vorm["subject"], p=vorm["predicate"])
    raise VormFout(f"onbekende vormsoort: {soort!r}")


def is_propositioneel(vorm: dict[str, Any]) -> bool:
    """Is deze vorm met een waarderingstabel te toetsen?

    Een ontkenning of implicatie telt alleen mee als alles wat zij omsluit dat
    ook doet. Anders zou een ontkende categorische bewering als propositioneel
    gelden en zou de waarderingstabel erop stukbreken.
    """
    soort = vorm["kind"]
    if soort == "atomic":
        return True
    if soort == "negation":
        return is_propositioneel(vorm["of"])
    if soort == "conditional":
        return is_propositioneel(vorm["antecedent"]) and is_propositioneel(vorm["consequent"])
    return False


def atomen(vorm: dict[str, Any]) -> set[str]:
    soort = vorm["kind"]
    if soort == "atomic":
        return {vorm["term"]}
    if soort == "negation":
        return atomen(vorm["of"])
    if soort == "conditional":
        return atomen(vorm["antecedent"]) | atomen(vorm["consequent"])
    return set()


def waarde(vorm: dict[str, Any], toekenning: dict[str, bool]) -> bool:
    soort = vorm["kind"]
    if soort == "atomic":
        return toekenning[vorm["term"]]
    if soort == "negation":
        return not waarde(vorm["of"], toekenning)
    if soort == "conditional":
        return (not waarde(vorm["antecedent"], toekenning)) or waarde(
            vorm["consequent"], toekenning
        )
    raise VormFout("alleen propositionele vormen zijn met een waarderingstabel te toetsen")


def _toekenningen(atoomlijst: list[str]):
    for combinatie in product((False, True), repeat=len(atoomlijst)):
        yield dict(zip(atoomlijst, combinatie, strict=True))


def vervulbaar(vormen: list[dict[str, Any]]) -> bool:
    """Bestaat er een toekenning waarin alle vormen waar zijn?"""
    atoomlijst = sorted(set().union(*(atomen(v) for v in vormen)) if vormen else set())
    return any(all(waarde(v, t) for v in vormen) for t in _toekenningen(atoomlijst))


def volgt_uit(premissen: list[dict[str, Any]], conclusie: dict[str, Any]) -> bool:
    """Propositionele gevolgtrekking via een volledige waarderingstabel."""
    alles = [*premissen, conclusie]
    atoomlijst = sorted(set().union(*(atomen(v) for v in alles)))
    for toekenning in _toekenningen(atoomlijst):
        if all(waarde(p, toekenning) for p in premissen) and not waarde(conclusie, toekenning):
            return False
    return True


def gelijk(links: dict[str, Any], rechts: dict[str, Any]) -> bool:
    return links == rechts


def _ontken(vorm: dict[str, Any]) -> dict[str, Any]:
    if vorm["kind"] == "negation":
        return vorm["of"]
    return {"kind": "negation", "of": vorm}


# --------------------------------------------------------------------------
# Categorische syllogistiek
# --------------------------------------------------------------------------

# Per kwantiteit: is het onderwerp gedistribueerd, is het gezegde gedistribueerd.
_DISTRIBUTIE = {
    "all": (True, False),
    "no": (True, True),
    "some": (False, False),
    "some_not": (False, True),
}


def _gedistribueerd(vorm: dict[str, Any], term: str) -> bool:
    onderwerp_verdeeld, gezegde_verdeeld = _DISTRIBUTIE[vorm["quantity"]]
    if vorm["subject"] == term and onderwerp_verdeeld:
        return True
    return bool(vorm["predicate"] == term and gezegde_verdeeld)


def _termen(vorm: dict[str, Any]) -> set[str]:
    return {vorm["subject"], vorm["predicate"]}


def _is_negatief(vorm: dict[str, Any]) -> bool:
    return vorm["quantity"] in NEGATIEVE_KWANTITEITEN


def _is_particulier(vorm: dict[str, Any]) -> bool:
    return vorm["quantity"] in PARTICULIERE_KWANTITEITEN


def syllogisme_geldig(
    premissen: list[dict[str, Any]], conclusie: dict[str, Any]
) -> tuple[bool, str, str | None]:
    """Toets een categorisch syllogisme.

    Geeft (geldig, toelichting, drogredensleutel). De drogredensleutel is
    ``undistributed_middle`` wanneer precies die regel breekt, en anders
    ``invalid_form_unnamed`` met een toelichting die de gebroken regel noemt.
    """
    if len(premissen) != 2:
        return (
            False,
            "een categorisch syllogisme heeft precies twee premissen; "
            f"er zijn er {'meer' if len(premissen) > 2 else 'minder'} aangeleverd",
            None,
        )
    # Let op: deze uitkomst betekent 'niet als syllogisme te toetsen', niet
    # 'ongeldig'. De aanroeper vertaalt haar naar not_testable.

    alle_termen = _termen(premissen[0]) | _termen(premissen[1]) | _termen(conclusie)
    if len(alle_termen) != 3:
        return (
            False,
            f"een categorisch syllogisme heeft precies drie termen; aangetroffen: "
            f"{', '.join(sorted(alle_termen))}",
            "invalid_form_unnamed",
        )

    # De structuurtoets moet verder gaan dan het tellen van drie verschillende
    # termen. Elke term hoort precies twee keer voor te komen: de conclusietermen
    # elk in één premisse, en de middenterm in beide. Telt de motor alleen het
    # aantal verschillende termen, dan laat zij een conclusie door met een term
    # die in geen enkele premisse staat, en dat is zekerheid uit niets.
    kleine_term = conclusie["subject"]
    grote_term = conclusie["predicate"]
    if kleine_term == grote_term:
        return (
            False,
            "de conclusie heeft dezelfde term als onderwerp en als gezegde",
            "invalid_form_unnamed",
        )
    midden_kandidaten = alle_termen - {kleine_term, grote_term}
    if len(midden_kandidaten) != 1:
        return (
            False,
            "de premissen en de conclusie delen geen enkele middenterm",
            "invalid_form_unnamed",
        )
    midden = midden_kandidaten.pop()

    for term, rol in ((kleine_term, "onderwerp"), (grote_term, "gezegde")):
        dragend = [p for p in premissen if term in _termen(p)]
        if len(dragend) != 1:
            hoeveel = "in geen enkele premisse" if not dragend else "in beide premissen"
            return (
                False,
                f"de term '{term}' staat als {rol} in de conclusie maar {hoeveel}; "
                "de premissen dragen die term dan niet",
                "invalid_form_unnamed",
            )
    for premisse in premissen:
        if midden not in _termen(premisse):
            return (
                False,
                f"de middenterm '{midden}' ontbreekt in de premisse "
                f"'{weergave(premisse)}'; zonder middenterm in beide premissen "
                "verbinden zij de uiterste termen niet",
                "invalid_form_unnamed",
            )

    if not any(_gedistribueerd(p, midden) for p in premissen):
        return (
            False,
            f"de middenterm '{midden}' is in geen van beide premissen gedistribueerd; "
            "de premissen spreken daardoor mogelijk over verschillende delen van die term",
            "undistributed_middle",
        )

    for term in _termen(conclusie):
        if _gedistribueerd(conclusie, term):
            premisse_met_term = next((p for p in premissen if term in _termen(p)), None)
            if premisse_met_term is None or not _gedistribueerd(premisse_met_term, term):
                rol = "gezegde" if term == conclusie["predicate"] else "onderwerp"
                return (
                    False,
                    f"de term '{term}' is als {rol} gedistribueerd in de conclusie maar niet in "
                    "haar premisse; de conclusie zegt meer over die term dan de premisse toestaat",
                    "invalid_form_unnamed",
                )

    negatieve_premissen = [p for p in premissen if _is_negatief(p)]
    if len(negatieve_premissen) == 2:
        return (
            False,
            "beide premissen zijn ontkennend; twee ontkenningen verbinden de uiterste termen niet",
            "invalid_form_unnamed",
        )
    if len(negatieve_premissen) == 1 and not _is_negatief(conclusie):
        return (
            False,
            "één premisse is ontkennend terwijl de conclusie bevestigend is",
            "invalid_form_unnamed",
        )
    if not negatieve_premissen and _is_negatief(conclusie):
        return (
            False,
            "beide premissen zijn bevestigend terwijl de conclusie ontkennend is",
            "invalid_form_unnamed",
        )

    if all(not _is_particulier(p) for p in premissen) and _is_particulier(conclusie):
        return (
            False,
            "uit twee universele premissen volgt geen particuliere conclusie onder de moderne "
            "lezing zonder existentiële import; zie docs/conventies-fase1.md",
            "invalid_form_unnamed",
        )

    return (True, "het syllogisme voldoet aan alle distributie- en kwaliteitsregels", None)


# --------------------------------------------------------------------------
# Uitkomst van de formele toets
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Drogreden:
    soort: str
    rationale: str


@dataclass(frozen=True)
class Kandidaat:
    """Een mogelijk verzwegen premisse. Een voorstel, geen vaststelling."""

    vorm: dict[str, Any]
    tekst: str
    basis: str
    rationale: str


@dataclass(frozen=True)
class VormAnalyse:
    status: str  # form_status: valid | invalid | not_testable
    rationale: str
    toetssoort: str  # propositioneel | categorisch | geen
    drogredenen: tuple[Drogreden, ...] = ()
    kandidaten: tuple[Kandidaat, ...] = ()
    ontbrekende_vormen: tuple[str, ...] = field(default=())
    # Waar of de zoektocht naar mogelijk verzwegen premissen is overgeslagen.
    # Een lege kandidatenlijst betekent dan niet "er is niets gevonden".
    kandidaatzoektocht_overgeslagen: bool = False


def _propositionele_drogredenen(
    premissen: list[dict[str, Any]], conclusie: dict[str, Any]
) -> list[Drogreden]:
    gevonden: list[Drogreden] = []
    voorwaardelijk = [p for p in premissen if p["kind"] == "conditional"]
    for regel in voorwaardelijk:
        antecedent = regel["antecedent"]
        consequent = regel["consequent"]
        overige = [p for p in premissen if p is not regel]
        if any(gelijk(p, consequent) for p in overige) and gelijk(conclusie, antecedent):
            gevonden.append(
                Drogreden(
                    "affirming_the_consequent",
                    f"uit '{weergave(regel)}' en '{weergave(consequent)}' wordt "
                    f"'{weergave(antecedent)}' afgeleid; het consequens bevestigen levert het "
                    "antecedent niet op, want het consequens kan ook langs een andere weg gelden",
                )
            )
        ontkend_antecedent = _ontken(antecedent)
        ontkend_consequent = _ontken(consequent)
        if any(gelijk(p, ontkend_antecedent) for p in overige) and gelijk(
            conclusie, ontkend_consequent
        ):
            gevonden.append(
                Drogreden(
                    "denying_the_antecedent",
                    f"uit '{weergave(regel)}' en '{weergave(ontkend_antecedent)}' wordt "
                    f"'{weergave(ontkend_consequent)}' afgeleid; het antecedent ontkennen sluit "
                    "het consequens niet uit",
                )
            )
    return gevonden


def _kandidaatvormen(atoomlijst: list[str]) -> list[dict[str, Any]]:
    letterlijk: list[dict[str, Any]] = []
    for atoom in atoomlijst:
        basis = {"kind": "atomic", "term": atoom}
        letterlijk.append(basis)
        letterlijk.append({"kind": "negation", "of": basis})
    kandidaten: list[dict[str, Any]] = list(letterlijk)
    for links, rechts in product(letterlijk, repeat=2):
        if atomen(links) == atomen(rechts):
            continue
        kandidaten.append({"kind": "conditional", "antecedent": links, "consequent": rechts})
    return kandidaten


def _propositionele_kandidaten(
    premissen: list[dict[str, Any]], conclusie: dict[str, Any]
) -> list[Kandidaat]:
    """Zoek de zwakste aannames die de stap sluitend zouden maken.

    Een kandidaat telt alleen mee als hij samen met de premissen de conclusie
    oplevert, de premissen niet tegenspreekt, en de conclusie niet in zijn
    eentje al oplevert. Dat laatste sluit 'neem de conclusie maar aan' uit.
    Van de overgebleven kandidaten blijven de logisch zwakste over: die vragen
    het minst van de lezer.
    """
    atoomlijst = sorted(set().union(*(atomen(v) for v in [*premissen, conclusie])))
    if not atoomlijst or len(atoomlijst) > MAX_ATOMEN_KANDIDATEN:
        return []
    voldoende: list[dict[str, Any]] = []
    for kandidaat in _kandidaatvormen(atoomlijst):
        if not vervulbaar([*premissen, kandidaat]):
            continue
        if volgt_uit([kandidaat], conclusie):
            continue
        if volgt_uit([*premissen, kandidaat], conclusie):
            voldoende.append(kandidaat)

    zwakste: list[dict[str, Any]] = []
    for kandidaat in voldoende:
        sterker_dan_ander = any(
            not gelijk(kandidaat, ander)
            and volgt_uit([kandidaat], ander)
            and not volgt_uit([ander], kandidaat)
            for ander in voldoende
        )
        if not sterker_dan_ander:
            zwakste.append(kandidaat)

    # Logisch equivalente kandidaten zeggen hetzelfde in andere woorden
    # (bijvoorbeeld een implicatie en haar contrapositie). Er blijft er één over.
    uniek: list[dict[str, Any]] = []
    for kandidaat in zwakste:
        gelijkwaardig = any(
            volgt_uit([kandidaat], bestaand) and volgt_uit([bestaand], kandidaat)
            for bestaand in uniek
        )
        if not gelijkwaardig:
            uniek.append(kandidaat)

    return [
        Kandidaat(
            vorm=kandidaat,
            tekst=weergave(kandidaat),
            basis="form_completion",
            rationale=(
                "de aangeleverde premissen leveren de conclusie niet op; met deze aanname erbij "
                "wel. De aanname is een voorstel dat op de vorm van de stap berust, geen "
                "vaststelling dat de auteur haar heeft weggelaten"
            ),
        )
        for kandidaat in sorted(uniek, key=lambda k: (len(weergave(k)), weergave(k)))
    ]


def _categorische_kandidaten(
    premissen: list[dict[str, Any]], conclusie: dict[str, Any]
) -> list[Kandidaat]:
    """Vul een categorisch enthymeem met één premisse aan."""
    if len(premissen) != 1:
        return []
    gegeven = premissen[0]
    conclusietermen = _termen(conclusie)
    overlappend = _termen(gegeven) & conclusietermen
    if len(overlappend) != 1:
        return []
    midden_kandidaten = _termen(gegeven) - conclusietermen
    if len(midden_kandidaten) != 1:
        return []
    midden = midden_kandidaten.pop()
    ontbrekende_term = (conclusietermen - overlappend).pop()

    gevonden: list[Kandidaat] = []
    for kwantiteit in ("all", "no", "some", "some_not"):
        for onderwerp, gezegde in ((ontbrekende_term, midden), (midden, ontbrekende_term)):
            kandidaat = {
                "kind": "categorical",
                "quantity": kwantiteit,
                "subject": onderwerp,
                "predicate": gezegde,
            }
            geldig, _, _ = syllogisme_geldig([gegeven, kandidaat], conclusie)
            if geldig and all(k.tekst != weergave(kandidaat) for k in gevonden):
                gevonden.append(
                    Kandidaat(
                        vorm=kandidaat,
                        tekst=weergave(kandidaat),
                        basis="form_completion",
                        rationale=(
                            "de stap heeft één categorische premisse en een conclusie; met deze "
                            "tweede premisse erbij wordt het een geldig syllogisme. Het is een "
                            "voorstel op grond van de vorm, geen vaststelling"
                        ),
                    )
                )
    return gevonden


def analyseer(
    premissen: list[Any], conclusie: Any, premisse_refs: list[str] | None = None
) -> VormAnalyse:
    """Toets een stap formeel, voor zover de aangeleverde vormen dat toelaten."""
    refs = premisse_refs or [f"premisse {i + 1}" for i in range(len(premissen))]

    zonder_vorm = [refs[i] for i, vorm in enumerate(premissen) if vorm is None]
    if conclusie is None:
        zonder_vorm = [*zonder_vorm, "conclusie"]
    if zonder_vorm:
        return VormAnalyse(
            status="not_testable",
            rationale=(
                "niet formeel getoetst: er is geen logische vorm aangeleverd voor "
                + ", ".join(zonder_vorm)
            ),
            toetssoort="geen",
            ontbrekende_vormen=tuple(zonder_vorm),
        )
    if not premissen:
        return VormAnalyse(
            status="not_testable",
            rationale="niet formeel getoetst: de stap heeft geen premissen",
            toetssoort="geen",
        )

    genormaliseerd = [normaliseer(v) for v in premissen]
    doel = normaliseer(conclusie)

    if any(gelijk(p, doel) for p in genormaliseerd):
        return VormAnalyse(
            status="invalid",
            rationale=(
                "de conclusie komt letterlijk als premisse voor; de stap steunt daarmee op zichzelf"
            ),
            toetssoort="propositioneel" if is_propositioneel(doel) else "categorisch",
            drogredenen=(
                Drogreden(
                    "circular_reasoning",
                    f"de premisse '{weergave(doel)}' is dezelfde propositie als de conclusie",
                ),
            ),
        )

    alles = [*genormaliseerd, doel]
    if all(is_propositioneel(v) for v in alles):
        return _analyseer_propositioneel(genormaliseerd, doel)
    if all(v["kind"] == "categorical" for v in alles):
        return _analyseer_categorisch(genormaliseerd, doel)
    return VormAnalyse(
        status="not_testable",
        rationale=(
            "niet formeel getoetst: de stap mengt propositionele en categorische vormen. "
            "Fase 1 toetst die combinatie niet; hieruit volgt niets over de geldigheid"
        ),
        toetssoort="geen",
    )


def _analyseer_propositioneel(
    premissen: list[dict[str, Any]], conclusie: dict[str, Any]
) -> VormAnalyse:
    if len(set().union(*(atomen(v) for v in [*premissen, conclusie]))) > MAX_ATOMEN:
        return VormAnalyse(
            status="not_testable",
            rationale=(
                "niet formeel getoetst: de stap bevat te veel losse termen voor een volledige "
                "waarderingstabel"
            ),
            toetssoort="propositioneel",
        )

    if not vervulbaar(premissen):
        return VormAnalyse(
            status="invalid",
            rationale=(
                "de premissen kunnen niet samen gelden; uit een tegenspraak volgt formeel alles, "
                "en de motor rekent dat niet als geldige steun"
            ),
            toetssoort="propositioneel",
            drogredenen=(
                Drogreden(
                    "contradictory_premises",
                    "er is geen enkele toestand waarin alle premissen tegelijk waar zijn",
                ),
            ),
        )

    if volgt_uit(premissen, conclusie):
        return VormAnalyse(
            status="valid",
            rationale=(
                "in elke toestand waarin alle premissen waar zijn, is de conclusie waar "
                "(volledige waarderingstabel)"
            ),
            toetssoort="propositioneel",
        )

    # Eén stap krijgt hooguit één naam. Passen twee patronen, dan is dat één
    # gebrek dat op twee manieren te beschrijven valt, geen twee gebreken.
    benoemd = _propositionele_drogredenen(premissen, conclusie)
    drogredenen = (benoemd[0],) if benoemd else ()
    if not drogredenen:
        drogredenen = (
            Drogreden(
                "invalid_form_unnamed",
                "er bestaat een toestand waarin alle premissen waar zijn en de conclusie onwaar; "
                "de stap heeft geen van de benoemde vormen",
            ),
        )
    aantal_atomen = len(set().union(*(atomen(v) for v in [*premissen, conclusie])))
    overgeslagen = aantal_atomen > MAX_ATOMEN_KANDIDATEN
    rationale = (
        "de conclusie volgt niet uit de premissen: er bestaat een toestand waarin alle "
        "premissen waar zijn en de conclusie onwaar"
    )
    if overgeslagen:
        rationale += (
            ". De zoektocht naar mogelijk verzwegen premissen is niet uitgevoerd: de stap "
            "bevat te veel losse termen. Dat er geen kandidaat wordt getoond, betekent hier "
            "dus niet dat er geen is"
        )
    return VormAnalyse(
        status="invalid",
        rationale=rationale,
        toetssoort="propositioneel",
        drogredenen=drogredenen,
        kandidaten=() if overgeslagen else tuple(_propositionele_kandidaten(premissen, conclusie)),
        kandidaatzoektocht_overgeslagen=overgeslagen,
    )


def _analyseer_categorisch(
    premissen: list[dict[str, Any]], conclusie: dict[str, Any]
) -> VormAnalyse:
    if len(premissen) == 1:
        kandidaten = tuple(_categorische_kandidaten(premissen, conclusie))
        return VormAnalyse(
            status="not_testable",
            rationale=(
                "niet als syllogisme te toetsen: er is één categorische premisse en een conclusie. "
                "Dat is de vorm van een enthymeem"
            ),
            toetssoort="categorisch",
            kandidaten=kandidaten,
        )

    geldig, toelichting, drogreden = syllogisme_geldig(premissen, conclusie)
    if geldig:
        return VormAnalyse(status="valid", rationale=toelichting, toetssoort="categorisch")
    if drogreden is None:
        # De vorm valt buiten wat fase 1 als syllogisme kan toetsen. Dat is geen
        # oordeel over de geldigheid: een sluitende sorites van drie premissen is
        # geldig, maar niet met deze toets vast te stellen. De motor bewijst geen
        # gat en noemt hem daarom niet ongeldig.
        return VormAnalyse(
            status="not_testable",
            rationale=(
                "niet formeel getoetst: " + toelichting + ". Fase 1 toetst uitsluitend "
                "syllogismen met twee premissen; hieruit volgt niets over de geldigheid"
            ),
            toetssoort="categorisch",
        )
    return VormAnalyse(
        status="invalid",
        rationale=toelichting,
        toetssoort="categorisch",
        drogredenen=(Drogreden(drogreden, toelichting),),
    )
