"""De ordinale sterkteschaal.

De schaal zelf is data: haar labels en hun ordening komen uit de lookup-tabel
``lu_strength_label``. Deze module bevat alleen de bewerkingen erop. De rangorde
is intern en verlaat de motor nooit als uitvoer (§2.5).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db.model import LOOKUP_KLASSEN
from .fouten import OnbekendeLookupwaarde


@dataclass(frozen=True)
class Schaal:
    """De geladen sterkteschaal, oplopend geordend."""

    oplopend: tuple[str, ...]
    _rang: dict[str, int]
    _label_nl: dict[str, str]

    @classmethod
    def uit_db(cls, sessie: Session) -> Schaal:
        klasse = LOOKUP_KLASSEN["strength_label"]
        rijen = sessie.execute(select(klasse).where(klasse.actief.is_(True))).scalars().all()
        if not rijen:
            raise OnbekendeLookupwaarde("de sterkteschaal is leeg; is de seed geladen?")
        ontbreekt = [r.key for r in rijen if r.rangorde is None]
        if ontbreekt:
            raise OnbekendeLookupwaarde(
                "sterktelabels zonder rangorde zijn niet te ordenen: "
                + ", ".join(sorted(ontbreekt))
            )
        geordend = sorted(rijen, key=lambda r: r.rangorde)
        return cls(
            oplopend=tuple(r.key for r in geordend),
            _rang={r.key: r.rangorde for r in geordend},
            _label_nl={r.key: r.label_nl for r in geordend},
        )

    def rang(self, label: str) -> int:
        try:
            return self._rang[label]
        except KeyError as fout:
            raise OnbekendeLookupwaarde(
                f"'{label}' staat niet in de sterkteschaal ({', '.join(self.oplopend)})"
            ) from fout

    def nl(self, label: str) -> str:
        self.rang(label)
        return self._label_nl[label]

    @property
    def laagste(self) -> str:
        return self.oplopend[0]

    @property
    def hoogste(self) -> str:
        return self.oplopend[-1]

    def minimum(self, labels) -> str:
        gevonden = list(labels)
        if not gevonden:
            return self.laagste
        return min(gevonden, key=self.rang)

    def maximum(self, labels) -> str:
        gevonden = list(labels)
        if not gevonden:
            return self.laagste
        return max(gevonden, key=self.rang)

    def boven(self, label: str) -> tuple[str, ...]:
        """Labels boven ``label``, van dichtstbij naar verst."""
        drempel = self.rang(label)
        return tuple(k for k in self.oplopend if self._rang[k] > drempel)

    def onder(self, label: str) -> tuple[str, ...]:
        """Labels onder ``label``, van dichtstbij naar verst."""
        drempel = self.rang(label)
        return tuple(reversed([k for k in self.oplopend if self._rang[k] < drempel]))
