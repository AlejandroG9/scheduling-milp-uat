# solvers/_base.py — lógica común para todos los solvers

from pathlib import Path
import copy
import time
import logging
import pandas as pd
from pyomo.environ import Var, Objective, value
from pyomo.util.infeasible import log_infeasible_constraints
from pyomo.opt import TerminationCondition as tc_enum
from model.update_data import actualizar_disponibilidades

DIAG_DIR = Path(__file__).resolve().parents[1] / "results" / "diagnosticos"
SOL_DIR  = Path(__file__).resolve().parents[1] / "results" / "solutions"


def _guardar_diagnostico(modelo, nombre):
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    with open(DIAG_DIR / f"{nombre}.txt", "w") as f:
        logger = logging.getLogger(nombre)
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(f)
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        log_infeasible_constraints(modelo, log_expression=True,
                                   log_variables=True, logger=logger)


def _extraer_solucion(modelo):
    sol_dict = {}
    for v in modelo.component_data_objects(Var, active=True, descend_into=True):
        val = getattr(v, "value", None)
        if val is not None and abs(val) > 1e-6:
            sol_dict[v.name] = float(val)
    return sol_dict


def _valor_objetivo(modelo):
    try:
        obj = next(modelo.component_data_objects(Objective, descend_into=True))
        return value(obj)
    except StopIteration:
        return None


def procesar_resultado(modelo, datos, results, solver_name, semestre, permutacion):
    """
    Procesa el resultado de cualquier solver y retorna una tupla estandarizada.

    Returns:
        datos_act : dict  — datos actualizados (None si infactible)
        obj_val   : float — valor de la función objetivo (None si infactible)
        status    : str   — 'optimal' | 'feasible' | 'timeout' | 'infeasible' | 'error'
        tiempo    : float — tiempo de resolución en segundos (ya medido por el caller)
        sol_dict  : dict  — variables activas (vacío si infactible)
    """
    tc = results.solver.termination_condition
    sc = results.solver.status
    print(f"[{solver_name}] status={sc}, termination={tc}")

    aceptables = {tc_enum.optimal, tc_enum.feasible, tc_enum.maxTimeLimit}

    if tc == tc_enum.infeasible:
        print(f"❌ [{solver_name}] Modelo infactible.")
        _guardar_diagnostico(modelo, f"diagnostico_{solver_name}_sem{semestre}")
        return None, None, "infeasible", {}, 0

    if tc not in aceptables:
        print(f"⚠️ [{solver_name}] Terminación inesperada: {tc}")
        return None, None, "error", {}, 0

    # Mapear termination condition a string legible
    if tc == tc_enum.optimal:
        status = "optimal"
    elif tc == tc_enum.maxTimeLimit:
        status = "timeout"
    else:
        status = "feasible"

    sol_dict  = _extraer_solucion(modelo)
    obj_val   = _valor_objetivo(modelo)
    datos_act = actualizar_disponibilidades(sol_dict, copy.deepcopy(datos))

    # Guardar CSV de solución
    SOL_DIR.mkdir(parents=True, exist_ok=True)
    rama     = "-".join(str(a) for a in permutacion)
    sol_csv  = SOL_DIR / f"Solucion_{solver_name}_sem{semestre}_{rama}.csv"
    pd.DataFrame.from_dict(sol_dict, orient="index", columns=["Valor"]).to_csv(sol_csv)
    print(f"✅ [{solver_name}] Solución guardada → {sol_csv.name}  |  obj={obj_val}  |  status={status}")

    return datos_act, obj_val, status, sol_dict, 0
