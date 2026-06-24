"""
runners/smoke_test.py — Prueba rápida con solver gratuito (HiGHS)

Corre 1 réplica del semestre 9 (la instancia más pequeña: 6 materias, 4 grupos)
para validar que el modelo construye y resuelve correctamente sin Gurobi.

Uso:
    .venv/bin/python runners/smoke_test.py
    .venv/bin/python runners/smoke_test.py --semestre 3
    .venv/bin/python runners/smoke_test.py --semestre 9 --solver cbc
"""

import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.loader import cargar_datos
from model.builder import crear_modelo_horarios
from model.utils import registrar_run
from scripts.init_db import init as init_db

SOLVERS_DISPONIBLES = ["highs", "cbc", "glpk"]


def main():
    parser = argparse.ArgumentParser(description="Smoke test — solver gratuito")
    parser.add_argument("--semestre", type=int, default=9,
                        help="Semestre a resolver (default: 9 — instancia más pequeña)")
    parser.add_argument("--solver", choices=SOLVERS_DISPONIBLES, default="highs",
                        help="Solver gratuito a usar (default: highs)")
    args = parser.parse_args()

    semestre = args.semestre
    solver   = args.solver

    print(f"\n{'='*60}")
    print(f"SMOKE TEST — Solver: {solver.upper()}  |  Semestre: {semestre}")
    print(f"{'='*60}\n")

    # Asegurar que la BD existe
    init_db()

    # Importar el solver seleccionado
    if solver == "highs":
        from solvers.highs import resolver_modelo_highs as resolver
    elif solver == "cbc":
        from solvers.cbc import resolver_modelo_cbc as resolver
    elif solver == "glpk":
        from solvers.glpk import resolver_modelo_glpk as resolver

    datos  = cargar_datos()
    modelo = crear_modelo_horarios(
        semestre    = semestre,
        permutacion = [semestre],
        datos       = copy.deepcopy(datos),
        huecos_grupo  = True,
        preferencias  = True,
        huecos_prof   = False,
        disjuntives   = False,
    )

    print(f"Modelo construido.")
    print(f"  Variables  : {sum(1 for _ in modelo.component_data_objects(__import__('pyomo.environ', fromlist=['Var']).Var, active=True, descend_into=True))}")
    print(f"  Restricciones: {sum(1 for _ in modelo.component_data_objects(__import__('pyomo.environ', fromlist=['Constraint']).Constraint, active=True, descend_into=True))}")
    print(f"\nResolviendo con {solver.upper()}...\n")

    sol_dict = {}
    try:
        datos_act, obj_val, status, tiempo, sol_dict = resolver(
            modelo, datos, permutacion=[semestre]
        )
    except Exception as exc:
        print(f"\n❌ Error al resolver: {exc}")
        status  = "error"
        obj_val = None
        tiempo  = None

    print(f"\n{'='*60}")
    print(f"RESULTADO")
    print(f"  Status    : {status}")
    print(f"  Obj. val  : {obj_val}")
    print(f"  Tiempo (s): {tiempo:.1f}" if tiempo is not None else "  Tiempo (s): N/A")
    print(f"{'='*60}\n")

    registrar_run(
        experiment      = "smoke_test",
        solver          = solver,
        semestre        = semestre,
        replica         = 1,
        status          = status,
        obj_val         = obj_val,
        tiempo_solver_s = tiempo,
        modelo          = modelo,
        huecos_grupo    = True,
        preferencias    = True,
        notas           = f"smoke_test_sem{semestre}_{solver}",
        sol_dict        = sol_dict,
    )

    if status in ("optimal", "feasible"):
        sol_dir = Path(__file__).resolve().parents[1] / "results" / "solutions"
        csvs = sorted(sol_dir.glob(f"Solucion_{solver}_sem{semestre}*.csv"))
        if csvs:
            import pandas as pd
            df = pd.read_csv(csvs[-1])
            print(f"Solución guardada en: {csvs[-1].name}")
            print(f"Variables activas   : {len(df)}\n")
        return 0
    else:
        print("⚠️  Sin solución factible.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
