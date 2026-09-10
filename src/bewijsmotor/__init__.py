"""Motor die de kwaliteit van bewijsvoering achter claims beoordeelt.

Fase 1: datamodel, kernregels, motor zonder inhoudelijke regels, nultest.
De werktitel van het product staat nergens in deze code; zie ``instelling.py``.
"""

MOTOR_VERSIE = "0.1.0"
# Welke fase van het bouwplan deze code implementeert. Dit is een eigenschap van
# de code, geen inhoudelijke regel: welke fase een gebruiksvorm nodig heeft,
# staat als data in de lookup-tabel.
GEBOUWDE_FASE = 1
CONTRACT_VERSIE = "1.0.0"
INVOERSCHEMA_VERSIE = "1.0.0"

__all__ = ["MOTOR_VERSIE", "CONTRACT_VERSIE", "INVOERSCHEMA_VERSIE", "GEBOUWDE_FASE"]
