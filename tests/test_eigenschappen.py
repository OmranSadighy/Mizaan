"""Eigenschapstests op de formele laag.

Hier wordt geen enkele conclusie getoetst, alleen eigenschappen die per geval
onafhankelijk na te rekenen zijn.
"""

from __future__ import annotations

import itertools
import random

from bewijsmotor.logica.vorm import syllogisme_geldig
from bewijsmotor.motor.graaf import zoek_cykels

KWANTITEITEN = ("all", "no", "some", "some_not")
LETTER = {"all": "A", "no": "E", "some": "I", "some_not": "O"}
FIGUREN = {
    1: (("M", "P"), ("S", "M")),
    2: (("P", "M"), ("S", "M")),
    3: (("M", "P"), ("M", "S")),
    4: (("P", "M"), ("M", "S")),
}
# De vijftien stemmingen die geldig zijn onder de moderne lezing zonder
# existentiële import. De negen die alleen mét existentiële import gelden
# (Darapti, Felapton, Bramantip, Fesapo, Barbari, Celaront, Cesaro, Camestros,
# Camenos) horen er niet bij; zie docs/conventies-fase1.md §3.
GELDIGE_STEMMINGEN = {
    "AAA-1",
    "EAE-1",
    "AII-1",
    "EIO-1",
    "AEE-2",
    "EAE-2",
    "AOO-2",
    "EIO-2",
    "IAI-3",
    "AII-3",
    "OAO-3",
    "EIO-3",
    "AEE-4",
    "IAI-4",
    "EIO-4",
}


def _categorisch(kwantiteit: str, onderwerp: str, gezegde: str) -> dict:
    return {
        "kind": "categorical",
        "quantity": kwantiteit,
        "subject": onderwerp,
        "predicate": gezegde,
    }


def test_precies_de_vijftien_geldige_stemmingen():
    gevonden = set()
    for figuur, (majeur, mineur) in FIGUREN.items():
        for q1, q2, q3 in itertools.product(KWANTITEITEN, repeat=3):
            geldig, _, _ = syllogisme_geldig(
                [_categorisch(q1, *majeur), _categorisch(q2, *mineur)],
                _categorisch(q3, "S", "P"),
            )
            if geldig:
                gevonden.add(f"{LETTER[q1]}{LETTER[q2]}{LETTER[q3]}-{figuur}")
    assert gevonden == GELDIGE_STEMMINGEN, (
        f"teveel: {sorted(gevonden - GELDIGE_STEMMINGEN)}; "
        f"gemist: {sorted(GELDIGE_STEMMINGEN - gevonden)}"
    )


def test_geen_geldig_syllogisme_met_een_conclusieterm_buiten_de_premissen():
    """Anders ontstaat er zekerheid over iets waar de premissen niets over zeggen."""
    termen = ("S", "P", "M")
    for q1, s1, p1 in itertools.product(KWANTITEITEN, termen, termen):
        if s1 == p1:
            continue
        for q2, s2, p2 in itertools.product(KWANTITEITEN, termen, termen):
            if s2 == p2:
                continue
            for q3, s3, p3 in itertools.product(KWANTITEITEN, termen, termen):
                if s3 == p3:
                    continue
                geldig, _, _ = syllogisme_geldig(
                    [_categorisch(q1, s1, p1), _categorisch(q2, s2, p2)],
                    _categorisch(q3, s3, p3),
                )
                if not geldig:
                    continue
                ongedekt = {s3, p3} - {s1, p1, s2, p2}
                assert not ongedekt, (
                    f"geldig verklaard terwijl {sorted(ongedekt)} in geen premisse voorkomt: "
                    f"{q1} {s1}-{p1}; {q2} {s2}-{p2} => {q3} {s3}-{p3}"
                )


def _knopen_die_werkelijk_in_een_kring_liggen(graaf: dict[str, set[str]]) -> set[str]:
    """Onafhankelijke nareken: welke knoop bereikt zichzelf?"""
    gevonden: set[str] = set()
    for start in graaf:
        stapel = [start]
        gezien = {start}
        while stapel:
            knoop = stapel.pop()
            for volgende in graaf.get(knoop, ()):
                if volgende == start:
                    gevonden.add(start)
                    stapel = []
                    break
                if volgende not in gezien:
                    gezien.add(volgende)
                    stapel.append(volgende)
    return gevonden


def test_kringdetectie_mist_niets_en_verzint_niets():
    """Een gemiste kring geeft een claim die op zichzelf steunt een positief label."""
    generator = random.Random(20260910)
    for _ in range(3000):
        aantal = generator.randint(1, 6)
        knopen = [chr(97 + i) for i in range(aantal)]
        graaf = {
            knoop: set(generator.sample(knopen, generator.randint(0, min(3, aantal))))
            for knoop in knopen
        }
        gevonden = {knoop for kring in zoek_cykels(graaf) for knoop in kring}
        werkelijk = _knopen_die_werkelijk_in_een_kring_liggen(graaf)
        assert gevonden == werkelijk, f"graaf {graaf}: {sorted(gevonden)} vs {sorted(werkelijk)}"
