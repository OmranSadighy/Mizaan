"""Controleer de acceptatiecriteria van fase 1 uit de herziene bouwspecificatie.

Draait de motor echt en toont per criterium het bewijs.

    .venv/bin/python scripts/acceptatie_fase1.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

WORTEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORTEL / "src"))

from sqlalchemy import select, text  # noqa: E402

from bewijsmotor.configuratie import (  # noqa: E402
    VARIABELE_DB,
    VARIABELE_SEED,
    VARIABELE_UITVOER,
    Configuratie,
)
from bewijsmotor.db.model import (  # noqa: E402
    CORPUS_TABELLEN,
    Assessment,
    AssessmentDependency,
    Base,
    Premise,
    QaidaStatusHistory,
)
from bewijsmotor.db.overzichten import OVERZICHTEN  # noqa: E402
from bewijsmotor.db.registry import (  # noqa: E402
    laad_seed,
    maak_engine,
    maak_schema,
    maak_sessiefabriek,
)
from bewijsmotor.motor.engine import Motor  # noqa: E402


def _regel(nummer: str, eis: str, geslaagd: bool, bewijs: str) -> bool:
    print(f"[{'groen' if geslaagd else 'ROOD':5}] {nummer}. {eis}")
    for lijn in bewijs.splitlines():
        print(f"          {lijn}")
    print()
    return geslaagd


def main() -> int:
    uitslagen: list[bool] = []

    engine = maak_engine()
    maak_schema(engine)
    sessie = maak_sessiefabriek(engine)()
    laad_seed(sessie)
    sessie.commit()

    motor = Motor(sessie)
    invoer = json.loads(
        (WORTEL / "voorbeelden" / "kalibratie_gebed.json").read_text(encoding="utf-8")
    )
    motor.beoordeel(invoer, actor="acceptatie")
    sessie.flush()

    premissen = sessie.execute(select(Premise)).scalars().all()
    zonder = [p.external_ref for p in premissen if not p.provenance]
    uitslagen.append(
        _regel(
            "1",
            "elke premisse heeft een expliciete provenance",
            not zonder and bool(premissen),
            f"premissen opgeslagen: {len(premissen)}\n"
            + "\n".join(f"{p.external_ref}: provenance = {p.provenance}" for p in premissen[:3])
            + "\nkolom is NOT NULL in het schema: "
            + str(not Premise.__table__.c.provenance.nullable),
        )
    )

    eerste = sessie.execute(select(Assessment)).scalars().all()
    eerste_id = eerste[0].id
    eerste_label = eerste[0].rapport["probative_force"]["label"]
    motor.beoordeel(invoer, actor="acceptatie")
    sessie.flush()
    alle = sessie.execute(select(Assessment)).scalars().all()
    opvolger = [a for a in alle if a.supersedes is not None]
    onveranderd = sessie.get(Assessment, eerste_id).rapport["probative_force"]["label"]
    sessie.commit()
    geblokkeerd = ""
    try:
        sessie.execute(
            text("UPDATE assessment SET competence_level = 'x' WHERE id = :i"), {"i": eerste_id}
        )
        geblokkeerd = "NIET GEBLOKKEERD"
    except Exception as fout:  # noqa: BLE001
        geblokkeerd = str(fout).split("\n")[0][:70]
        sessie.rollback()
    uitslagen.append(
        _regel(
            "2",
            "tweede beoordeling maakt een nieuwe rij met supersedes en overschrijft niets",
            len(alle) == 2 and len(opvolger) == 1 and onveranderd == eerste_label,
            f"beoordelingen na twee runs: {len(alle)}\n"
            f"opvolger.supersedes == eerste.id: {opvolger[0].supersedes == eerste_id}\n"
            f"eerste rij ongewijzigd: label nog steeds {onveranderd}\n"
            f"poging tot overschrijven: {geblokkeerd}",
        )
    )

    per_beoordeling = {
        a.id: sessie.execute(
            select(AssessmentDependency.dependency_kind)
            .where(AssessmentDependency.assessment_id == a.id)
            .distinct()
        )
        .scalars()
        .all()
        for a in alle
    }
    alle_gevuld = all(soorten for soorten in per_beoordeling.values())
    uitslagen.append(
        _regel(
            "3",
            "assessment_dependency wordt bij elke beoordeling gevuld",
            alle_gevuld,
            "\n".join(
                f"beoordeling {kort[:8]}: {', '.join(sorted(soorten))}"
                for kort, soorten in per_beoordeling.items()
            ),
        )
    )

    corpus = {
        naam: sessie.execute(text(f"SELECT COUNT(*) FROM {naam}")).scalar_one()
        for naam in CORPUS_TABELLEN
    }
    uitslagen.append(
        _regel(
            "4",
            "de corpustabellen bestaan en zijn leeg",
            all(naam in Base.metadata.tables for naam in CORPUS_TABELLEN)
            and all(aantal == 0 for aantal in corpus.values()),
            "\n".join(f"{naam}: {aantal} rijen" for naam, aantal in corpus.items()),
        )
    )

    historie_bestaat = "qaida_status_history" in Base.metadata.tables
    kolommen = sorted(kolom.name for kolom in QaidaStatusHistory.__table__.columns)
    uitslagen.append(
        _regel(
            "5",
            "qaida_status_history bestaat",
            historie_bestaat,
            "kolommen: " + ", ".join(kolommen),
        )
    )

    overzichten = {
        naam: sessie.execute(text(f"SELECT COUNT(*) FROM {naam}")).scalar_one()
        for naam in OVERZICHTEN
    }
    uitslagen.append(
        _regel(
            "6",
            "de afgeleide overzichten uit §5.12 bestaan",
            len(overzichten) == len(OVERZICHTEN),
            "\n".join(f"{naam}: {aantal} rijen" for naam, aantal in overzichten.items()),
        )
    )

    lockfile = WORTEL / "requirements.lock"
    hashes = (
        lockfile.read_text(encoding="utf-8").count("--hash=sha256:") if lockfile.exists() else 0
    )
    pyproject = (WORTEL / "pyproject.toml").read_text(encoding="utf-8")
    losse_bereiken = [
        regel.strip()
        for regel in pyproject.splitlines()
        if (">=" in regel or "~=" in regel) and '"' in regel and "requires-python" not in regel
    ]
    uitslagen.append(
        _regel(
            "7",
            "afhankelijkheden hard vastgepind, met lockfile",
            lockfile.exists() and hashes > 0 and not losse_bereiken,
            f"lockfile: {lockfile.name} met {hashes} inhoudshashes\n"
            f"versiebereiken in pyproject.toml: {losse_bereiken or 'geen'}\n"
            "installeren met: pip install --require-hashes -r requirements.lock",
        )
    )

    omgeving = Configuratie.uit_omgeving()
    gezet = {
        VARIABELE_DB: "/tmp/proef.sqlite3",
        VARIABELE_SEED: str(WORTEL / "seed"),
        VARIABELE_UITVOER: "/tmp/proef-uitvoer",
    }
    uitkomst = subprocess.run(
        [sys.executable, "-m", "bewijsmotor.cli", "configuratie"],
        capture_output=True,
        text=True,
        cwd=str(WORTEL),
        env={**os.environ, **gezet, "PYTHONPATH": "src"},
        check=False,
    )
    volgt_omgeving = all(f"{k}={v}" in uitkomst.stdout for k, v in gezet.items())
    uitslagen.append(
        _regel(
            "8",
            "configuratie buiten de code: paden uit omgevingsvariabelen",
            volgt_omgeving,
            "standaard zonder omgeving:\n"
            + "\n".join(f"  {k}={v}" for k, v in omgeving.als_dict().items())
            + "\nmet omgeving gezet:\n"
            + "".join(f"  {lijn}\n" for lijn in uitkomst.stdout.strip().splitlines()),
        )
    )

    sessie.close()
    print("-" * 72)
    if all(uitslagen):
        print("Alle acceptatiecriteria van fase 1 zijn groen.")
        return 0
    print("Er is een criterium rood.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
