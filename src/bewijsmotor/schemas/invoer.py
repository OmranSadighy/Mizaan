"""Invoercontract: handmatig gestructureerde JSON.

Bewust géén enum of Literal op een inhoudelijk veld. Alle vocabulairewaarden
zijn hier gewone tekst; of de waarde bestaat, wordt getoetst tegen de
lookup-tabellen in de database (§2.9). Zo blijft de vraag welke lijsten gesloten
mogen zijn een vraag voor de data, niet voor het schema.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strikt(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ScoreInvoer(Strikt):
    label: str
    rationale: str = Field(min_length=1)
    computed_by: str = "manual_input"
    version: str | None = None
    instrument: str | None = None


class CitatieInvoer(Strikt):
    source_ref: str | None = None
    verification_status: str = "unverified"


class HerkomstInvoer(Strikt):
    """Verplichte herkomst van een premisse (§5.6)."""

    kind: str
    detail: dict[str, Any] | None = None
    corpus_document_ref: str | None = None


class StatusInvoer(Strikt):
    """Een statuslabel draagt altijd de tegenstelling waarin het gebruikt wordt."""

    label: str = Field(min_length=1)
    opposition: str = Field(min_length=1)


class KritischeVraagInvoer(Strikt):
    # Verwijst naar het volgnummer van een basisvraag bij het schema; leeg
    # betekent een eigen vraag die niet in de geseede vragenset staat.
    template: str | None = None
    question: str = Field(min_length=1)
    status: str = "unanswered"
    effect: str = "none"
    toelichting: str | None = None


class PremisseInvoer(Strikt):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    type: str | None = None
    explicit: bool = True
    provenance: HerkomstInvoer
    citation: CitatieInvoer | None = None
    thubut: ScoreInvoer | None = None
    dalalah: ScoreInvoer | None = None
    status: StatusInvoer | None = None
    sub_premises: list[PremisseInvoer] = Field(default_factory=list)
    form: dict[str, Any] | str | None = None
    terms: list[str] = Field(default_factory=list)
    asserts_claim: str | None = None
    proposed_by: str = "user"
    confirmed: bool = True
    instrument_output: dict[str, Any] | None = None


class ClaimInvoer(Strikt):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    form: dict[str, Any] | str | None = None
    terms: list[str] = Field(default_factory=list)


class InferentieInvoer(Strikt):
    id: str = Field(min_length=1)
    van: list[str] = Field(alias="from", default_factory=list)
    naar: str = Field(alias="to")
    scheme: str | None = None
    interpretation_ref: str | None = None
    critical_questions: list[KritischeVraagInvoer] = Field(default_factory=list)
    strength: ScoreInvoer | None = None
    proposed_by: str = "user"
    confirmed: bool = True


class InzendingKop(Strikt):
    id: str | None = None
    title: str | None = None
    language: str | None = None


class InzendingInvoer(Strikt):
    # Toelichting in het invoerbestand zelf; wordt bewaard, niet beoordeeld.
    toelichting: str | None = Field(default=None, alias="_toelichting")
    schema_version: str
    submission: InzendingKop = Field(default_factory=InzendingKop)
    profile: str = "leeg"
    profile_version: str | None = None
    competence_level: str = "unrestricted"
    use_form: str = "assess"
    claims: list[ClaimInvoer] = Field(default_factory=list)
    premises: list[PremisseInvoer] = Field(default_factory=list)
    inferences: list[InferentieInvoer] = Field(default_factory=list)

    @model_validator(mode="after")
    def _minimaal_een_claim(self) -> InzendingInvoer:
        if not self.claims:
            raise ValueError(
                "een inzending zonder claims is niet te beoordelen: er is dan niets bepaald "
                "waarover geoordeeld kan worden (kernregel oordeel_vereist_begrip)"
            )
        return self


PremisseInvoer.model_rebuild()
InzendingInvoer.model_rebuild()
