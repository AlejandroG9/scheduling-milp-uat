"""
runners/benchmark.py — E2: Comparación de solvers (A1)
Corre Gurobi, HiGHS, CBC y GLPK sobre semestres representativos.
- S9: instancia pequeña  (6 materias, 4 grupos)
- S3: instancia mediana  (8 materias, 4 grupos)
- S1: instancia grande   (8 materias, 5 grupos)
"""

import copy
from data.loader import cargar_datos
from model.builder import crear_modelo_horarios
from solvers.gurobi import resolver_modelo_gurobi
from solvers.cbc    import resolver_modelo_cbc
from solvers.glpk   import resolver_modelo_glpk
from solvers.highs  import resolver_modelo_highs
from model.utils    import registrar_run

SEMESTRES_BENCHMARK = [9, 3, 1]   # pequeño, mediano, grande
REPLICAS            = 5            # réplicas por solver/semestre
EXPERIMENT          = "benchmark"

SOLVERS = {
    "gurobi": resolver_modelo_gurobi,
    "highs":  resolver_modelo_highs,
    "cbc":    resolver_modelo_cbc,
    "glpk":   resolver_modelo_glpk,
}


def main():
    for semestre in SEMESTRES_BENCHMARK:
        for solver_name, resolver in SOLVERS.items():
            print(f"\n{'='*60}")
            print(f"BENCHMARK — Solver: {solver_name.upper()}  |  Semestre: {semestre}")
            print(f"{'='*60}")

            for replica in range(1, REPLICAS + 1):
                print(f"\n--- Réplica {replica}/{REPLICAS} ---")

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

                try:
                    datos_act, obj_val, status, tiempo = resolver(
                        modelo, datos, permutacion=[semestre]
                    )
                except Exception as e:
                    print(f"⚠️ [{solver_name}] Error: {e}")
                    status  = "error"
                    obj_val = None
                    tiempo  = None

                registrar_run(
                    experiment      = EXPERIMENT,
                    solver          = solver_name,
                    semestre        = semestre,
                    replica         = replica,
                    status          = status,
                    obj_val         = obj_val,
                    tiempo_solver_s = tiempo,
                    modelo          = modelo,
                    huecos_grupo    = True,
                    preferencias    = True,
                    notas           = f"benchmark_sem{semestre}",
                )


if __name__ == "__main__":
    main()
