"""
runners/full_experiment.py — E1: Experimento principal
9 semestres × 30 réplicas independientes con Gurobi.
Configuración: huecos_grupo=True, preferencias=True.
"""

import copy
from data.loader import cargar_datos
from model.builder import crear_modelo_horarios
from solvers.gurobi import resolver_modelo_gurobi
from model.utils import registrar_run

SEMESTRES  = list(range(1, 10))   # 1 al 9
REPLICAS   = 30
EXPERIMENT = "full"


def main():
    for semestre in SEMESTRES:
        print(f"\n{'='*60}")
        print(f"SEMESTRE {semestre}")
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

            datos_act, obj_val, status, tiempo = resolver_modelo_gurobi(
                modelo, datos, permutacion=[semestre]
            )

            registrar_run(
                experiment   = EXPERIMENT,
                solver       = "gurobi",
                semestre     = semestre,
                replica      = replica,
                status       = status,
                obj_val      = obj_val,
                tiempo_solver_s = tiempo,
                modelo       = modelo,
                huecos_grupo = True,
                preferencias = True,
            )


if __name__ == "__main__":
    main()
