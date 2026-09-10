"""Configuratie buiten de code (§11, fase 1)."""

from __future__ import annotations

import pytest

from bewijsmotor.configuratie import (
    STANDAARD_DB,
    VARIABELE_DB,
    VARIABELE_SEED,
    VARIABELE_UITVOER,
    Configuratie,
)
from bewijsmotor.fouten import ConfiguratieFout


def test_zonder_omgeving_gelden_de_standaardwaarden(monkeypatch):
    for naam in (VARIABELE_DB, VARIABELE_SEED, VARIABELE_UITVOER):
        monkeypatch.delenv(naam, raising=False)
    configuratie = Configuratie.uit_omgeving()
    assert configuratie.databasepad == STANDAARD_DB
    assert configuratie.seed_map.name == "seed"
    assert configuratie.uitvoer_map.name == "uitvoer"


def test_de_omgeving_wint_van_de_standaard(monkeypatch, tmp_path):
    monkeypatch.setenv(VARIABELE_DB, str(tmp_path / "eigen.sqlite3"))
    monkeypatch.setenv(VARIABELE_SEED, str(tmp_path))
    monkeypatch.setenv(VARIABELE_UITVOER, str(tmp_path / "uit"))
    configuratie = Configuratie.uit_omgeving()
    assert configuratie.databasepad.endswith("eigen.sqlite3")
    assert configuratie.database_url.endswith("eigen.sqlite3")
    assert configuratie.klaargezette_uitvoer_map().is_dir()


def test_een_lege_waarde_is_een_vergissing_en_geen_keuze(monkeypatch):
    monkeypatch.setenv(VARIABELE_DB, "   ")
    with pytest.raises(ConfiguratieFout, match="gezet maar leeg"):
        Configuratie.uit_omgeving()


def test_een_niet_bestaande_seed_map_wordt_gemeld(monkeypatch, tmp_path):
    monkeypatch.setenv(VARIABELE_SEED, str(tmp_path / "bestaat-niet"))
    with pytest.raises(ConfiguratieFout, match="bestaat niet"):
        Configuratie.uit_omgeving().controleer_seed()


def test_geen_pad_staat_hardgecodeerd_in_de_motor():
    """Alleen de configuratiemodule mag een standaardpad noemen."""
    import pathlib

    bron = pathlib.Path(__file__).resolve().parents[1] / "src" / "bewijsmotor"
    overtredingen = []
    for pad in bron.rglob("*.py"):
        if pad.name == "configuratie.py":
            continue
        for nummer, regel in enumerate(pad.read_text(encoding="utf-8").splitlines(), start=1):
            if ".sqlite3" in regel or '"/home' in regel or "'/home" in regel:
                overtredingen.append(f"{pad.name}:{nummer}")
    assert overtredingen == [], f"hardgecodeerde paden: {overtredingen}"
