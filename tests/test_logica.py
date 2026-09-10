"""De formele toetsen. Vorm, en niets dan vorm."""

from __future__ import annotations

import pytest

from bewijsmotor.logica.vorm import VormFout, analyseer, normaliseer, syllogisme_geldig, weergave


def A(term):
    return {"kind": "atomic", "term": term}


def N(vorm):
    return {"kind": "negation", "of": vorm}


def C(antecedent, consequent):
    return {"kind": "conditional", "antecedent": antecedent, "consequent": consequent}


def K(kwantiteit, onderwerp, gezegde):
    return {
        "kind": "categorical",
        "quantity": kwantiteit,
        "subject": onderwerp,
        "predicate": gezegde,
    }


@pytest.mark.parametrize(
    ("premissen", "conclusie"),
    [
        ([C(A("p"), A("q")), A("p")], A("q")),
        ([C(A("p"), A("q")), N(A("q"))], N(A("p"))),
        ([C(A("p"), A("q")), C(A("q"), A("r")), A("p")], A("r")),
        (
            [K("all", "mens", "sterfelijk"), K("all", "griek", "mens")],
            K("all", "griek", "sterfelijk"),
        ),
        ([K("no", "vis", "zoogdier"), K("all", "walvis", "zoogdier")], K("no", "walvis", "vis")),
    ],
)
def test_geldige_vormen(premissen, conclusie):
    assert analyseer(premissen, conclusie).status == "valid"


@pytest.mark.parametrize(
    ("premissen", "conclusie", "drogreden"),
    [
        ([C(A("p"), A("q")), A("q")], A("p"), "affirming_the_consequent"),
        ([C(A("p"), A("q")), N(A("p"))], N(A("q")), "denying_the_antecedent"),
        (
            [K("all", "hond", "zoogdier"), K("all", "kat", "zoogdier")],
            K("all", "kat", "hond"),
            "undistributed_middle",
        ),
        ([A("p"), N(A("p"))], A("q"), "contradictory_premises"),
    ],
)
def test_ongeldige_vormen_met_naam(premissen, conclusie, drogreden):
    analyse = analyseer(premissen, conclusie)
    assert analyse.status == "invalid"
    assert drogreden in {d.soort for d in analyse.drogredenen}


def test_cirkelvorm_is_geldig_maar_draagt_niets():
    """P volgt uit P; de vorm faalt niet, de steun ontbreekt.

    Juist de kernregel die hier wordt aangeroepen, vorm_versus_waarheid, staat
    op dat onderscheid. De stap heet daarom geldig, met een cirkelbevinding
    erbij en de vlag dat zij niets draagt.
    """
    analyse = analyseer([A("p"), A("q")], A("p"))
    assert analyse.status == "valid"
    assert analyse.zelfsteun is True
    assert "circular_reasoning" in {d.soort for d in analyse.drogredenen}
    assert "draagt niets" in analyse.rationale
    assert "vooronderstelt wat zij moet opleveren" in analyse.rationale


def test_tegenspraak_levert_geen_geldige_stap_op():
    """Uit een tegenspraak volgt formeel alles; de motor rekent dat niet als steun."""
    analyse = analyseer([A("p"), N(A("p"))], A("wat_dan_ook"))
    assert analyse.status == "invalid"
    assert "tegenspraak" in analyse.rationale


def test_moderne_lezing_zonder_existentiele_import():
    """Uit twee universele premissen volgt geen particuliere conclusie."""
    analyse = analyseer(
        [K("all", "m", "p"), K("all", "m", "s")],
        K("some", "s", "p"),
    )
    assert analyse.status == "invalid"
    assert "existentiële import" in analyse.rationale


def test_zonder_vorm_wordt_niets_beweerd():
    analyse = analyseer([None, A("p")], A("q"))
    assert analyse.status == "not_testable"
    assert analyse.drogredenen == ()
    assert "geen logische vorm aangeleverd" in analyse.rationale


def test_kandidaat_is_de_zwakste_aanname_en_nooit_de_conclusie_zelf():
    analyse = analyseer([A("gebod")], A("verplicht"))
    teksten = [kandidaat.tekst for kandidaat in analyse.kandidaten]
    assert teksten == ["als gebod, dan verplicht"]
    assert "verplicht" not in [kandidaat.vorm.get("term") for kandidaat in analyse.kandidaten]


def test_categorisch_enthymeem_wordt_aangevuld():
    analyse = analyseer([K("all", "griek", "mens")], K("all", "griek", "sterfelijk"))
    assert analyse.status == "not_testable"
    assert "alle mens zijn sterfelijk" in [kandidaat.tekst for kandidaat in analyse.kandidaten]


def test_syllogismeregels_afzonderlijk():
    geldig, toelichting, _ = syllogisme_geldig(
        [K("all", "m", "p"), K("all", "s", "m")], K("all", "s", "p")
    )
    assert geldig, toelichting

    geldig, toelichting, sleutel = syllogisme_geldig(
        [K("no", "m", "p"), K("no", "s", "m")], K("all", "s", "p")
    )
    assert not geldig
    assert "ontkennend" in toelichting

    geldig, toelichting, sleutel = syllogisme_geldig(
        [K("all", "m", "p"), K("all", "s", "m")], K("no", "s", "p")
    )
    assert not geldig
    assert sleutel == "invalid_form_unnamed"


def test_normaliseren_en_weergeven():
    assert normaliseer("p") == {"kind": "atomic", "term": "p"}
    assert weergave(C(A("p"), A("q"))) == "als p, dan q"
    assert weergave(K("some_not", "s", "p")) == "sommige s zijn niet p"
    with pytest.raises(VormFout):
        normaliseer({"kind": "onbekend"})
    with pytest.raises(VormFout):
        normaliseer({"kind": "categorical", "quantity": "veel", "subject": "s", "predicate": "p"})
