"""
runners/sensitivity.py — E3: Análisis de sensibilidad de pesos (A3)
Varía los parámetros tn, md, ags de forma independiente y cruzada.
Semestre fijo: S9 (más rápido) para iterar muchos escenarios.
"""

import copy
import itertools
import pyomo.environ as pyo
from data.loader import cargar_datos
from model.builder import crear_modelo_horarios
from solvers.gurobi import resolver_modelo_gurobi
from model.utils    import registrar_run, ya_ejecutado

SEMESTRE   = 9        # semestre de referencia para sensibilidad
REPLICAS   = 10        # réplicas por escenario
EXPERIMENT = "sensitivity"

# Factores de escala para cada parámetro (1.0 = base)
FACTORES = [0.5, 1.0, 2.0, 5.0]


def escalar_parametro(modelo, param_name, factor):
    """Multiplica todos los valores de un parámetro Pyomo por un factor."""
    param = getattr(modelo, param_name)
    for idx in param:
        param[idx].set_value(pyo.value(param[idx]) * factor)


def main():
    # ── Sensibilidad independiente: variar un parámetro a la vez ──────────
    for param_name, factor in itertools.product(['tn', 'md', 'ags'], FACTORES):
        if factor == 1.0:
            continue   # caso base ya cubierto en full_experiment

        notas_escenario = f"{param_name}_x{factor}"
        print(f"\n{'='*60}")
        print(f"SENSITIVITY — {param_name} × {factor}  |  Semestre {SEMESTRE}")
        print(f"{'='*60}")

        for replica in range(1, REPLICAS + 1):
            if ya_ejecutado(EXPERIMENT, "gurobi", SEMESTRE, replica, notas=notas_escenario):
                print(f"  [skip] {notas_escenario}/rep{replica} ya completado")
                continue

            datos  = cargar_datos()
            modelo = crear_modelo_horarios(
                semestre    = SEMESTRE,
                permutacion = [SEMESTRE],
                datos       = copy.deepcopy(datos),
                huecos_grupo = True,
                preferencias = True,
            )

            escalar_parametro(modelo, param_name, factor)

            datos_act, obj_val, status, tiempo, sol_dict = resolver_modelo_gurobi(
                modelo, datos, permutacion=[SEMESTRE]
            )

            registrar_run(
                experiment      = EXPERIMENT,
                solver          = "gurobi",
                semestre        = SEMESTRE,
                replica         = replica,
                status          = status,
                obj_val         = obj_val,
                tiempo_solver_s = tiempo,
                modelo          = modelo,
                huecos_grupo    = True,
                preferencias    = True,
                peso_tn         = factor if param_name == 'tn'  else 1.0,
                peso_md         = factor if param_name == 'md'  else 1.0,
                peso_ags        = factor if param_name == 'ags' else 1.0,
                notas           = notas_escenario,
                sol_dict        = sol_dict,
            )

    # ── Caso base (todos en 1.0) ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"SENSITIVITY — caso base (tn=md=ags=1.0)  |  Semestre {SEMESTRE}")
    print(f"{'='*60}")

    for replica in range(1, REPLICAS + 1):
        if ya_ejecutado(EXPERIMENT, "gurobi", SEMESTRE, replica, notas="base"):
            print(f"  [skip] base/rep{replica} ya completado")
            continue

        datos  = cargar_datos()
        modelo = crear_modelo_horarios(
            semestre    = SEMESTRE,
            permutacion = [SEMESTRE],
            datos       = copy.deepcopy(datos),
            huecos_grupo = True,
            preferencias = True,
        )

        datos_act, obj_val, status, tiempo, sol_dict = resolver_modelo_gurobi(
            modelo, datos, permutacion=[SEMESTRE]
        )

        registrar_run(
            experiment      = EXPERIMENT,
            solver          = "gurobi",
            semestre        = SEMESTRE,
            replica         = replica,
            status          = status,
            obj_val         = obj_val,
            tiempo_solver_s = tiempo,
            modelo          = modelo,
            huecos_grupo    = True,
            preferencias    = True,
            peso_tn         = 1.0,
            peso_md         = 1.0,
            peso_ags        = 1.0,
            notas           = "base",
            sol_dict        = sol_dict,
        )


if __name__ == "__main__":
    main()
