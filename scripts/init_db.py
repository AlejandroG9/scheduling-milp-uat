"""
Inicializa la base de datos SQLite con el esquema de experimentación.
Ejecutar una vez antes de correr cualquier experimento.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "results" / "experiments.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Runs ────────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment      TEXT    NOT NULL,   -- 'benchmark', 'sensitivity', 'full'
            release_id      TEXT    NOT NULL,   -- hash del dataset usado
            solver          TEXT    NOT NULL,   -- 'gurobi', 'cbc', 'glpk', 'highs'
            semestre        INTEGER NOT NULL,
            permutacion     TEXT,               -- ej. '1-3-5-9'
            huecos_grupo    INTEGER NOT NULL DEFAULT 1,
            huecos_prof     INTEGER NOT NULL DEFAULT 0,
            preferencias    INTEGER NOT NULL DEFAULT 0,
            disjuntives     INTEGER NOT NULL DEFAULT 0,
            -- pesos de sensibilidad (A3)
            peso_tn         REAL,
            peso_md         REAL,
            peso_ags        REAL,
            -- métricas de ejecución
            status          TEXT,               -- 'optimal', 'feasible', 'infeasible', 'timeout'
            obj_val         REAL,
            tiempo_total_s  REAL,
            tiempo_solver_s REAL,
            cpu_percent     REAL,
            ram_percent     REAL,
            n_variables     INTEGER,
            n_restricciones INTEGER,
            -- trazabilidad
            modelo_version  TEXT,
            fecha           TEXT DEFAULT (datetime('now')),
            notas           TEXT
        );
    """)

    # ── Soluciones (variable X activa) ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS solucion_x (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL REFERENCES runs(id),
            profesor    TEXT    NOT NULL,
            materia     TEXT    NOT NULL,
            dia         TEXT    NOT NULL,
            hora        INTEGER NOT NULL,
            aula        TEXT    NOT NULL,
            grupo       TEXT    NOT NULL,
            valor       REAL    NOT NULL
        );
    """)

    # ── Variable W (huecos de grupos) ───────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS solucion_w (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id  INTEGER NOT NULL REFERENCES runs(id),
            dia     TEXT    NOT NULL,
            hora    INTEGER NOT NULL,
            grupo   TEXT    NOT NULL,
            valor   REAL    NOT NULL
        );
    """)

    # ── Variable R (preferencias) ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS solucion_r (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id   INTEGER NOT NULL REFERENCES runs(id),
            materia  TEXT    NOT NULL,
            dia      TEXT    NOT NULL,
            hora     INTEGER NOT NULL,
            aula     TEXT    NOT NULL,
            grupo    TEXT    NOT NULL,
            valor    REAL    NOT NULL
        );
    """)

    # ── Índices para consultas frecuentes ───────────────────────────────────
    cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs(experiment);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_solver     ON runs(solver);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_semestre   ON runs(semestre);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sol_x_run       ON solucion_x(run_id);")

    conn.commit()
    conn.close()
    print(f"Base de datos inicializada en {DB_PATH}")


if __name__ == "__main__":
    init()
