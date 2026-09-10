"""Afhankelijkheden hard vastgepind (§11, fase 1)."""

from __future__ import annotations

import re
from pathlib import Path

WORTEL = Path(__file__).resolve().parents[1]


def test_er_is_een_lockfile_met_inhoudshashes():
    lockfile = WORTEL / "requirements.lock"
    assert lockfile.exists()
    tekst = lockfile.read_text(encoding="utf-8")
    pakketten = re.findall(r"^([A-Za-z0-9_.\-]+)==", tekst, flags=re.MULTILINE)
    hashes = re.findall(r"--hash=sha256:[0-9a-f]{64}", tekst)
    assert len(pakketten) >= 10
    assert len(hashes) == len(pakketten), "elk pakket hoort een inhoudshash te dragen"
    assert "SQLAlchemy" in pakketten and "pydantic" in pakketten


def test_geen_versiebereik_in_pyproject():
    """Een bereik laat een andere bibliotheek toe, en die kan een ander antwoord geven."""
    tekst = (WORTEL / "pyproject.toml").read_text(encoding="utf-8")
    bereiken = [
        regel.strip()
        for regel in tekst.splitlines()
        if ('">=' in regel or '"~=' in regel or "'>=" in regel) and "requires-python" not in regel
    ]
    assert bereiken == [], f"versiebereiken gevonden: {bereiken}"


def test_de_gepinde_versies_komen_overeen_met_de_lockfile():
    pyproject = (WORTEL / "pyproject.toml").read_text(encoding="utf-8")
    lockfile = (WORTEL / "requirements.lock").read_text(encoding="utf-8")
    for pakket in ("SQLAlchemy", "pydantic", "pytest", "ruff"):
        gepind = re.search(rf'"{pakket}==([^"]+)"', pyproject)
        vergrendeld = re.search(rf"^{pakket}==(.+?) \\", lockfile, flags=re.MULTILINE)
        assert gepind and vergrendeld, f"{pakket} ontbreekt"
        assert gepind.group(1) == vergrendeld.group(1), (
            f"{pakket}: pyproject zegt {gepind.group(1)}, lockfile zegt {vergrendeld.group(1)}"
        )
