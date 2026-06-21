# optim/solvers/cbc.py

from pathlib import Path
import copy
import pandas as pd
import logging
from pyomo.opt import SolverFactory
from pyomo.environ import Var, Objective, value
from model.update_data import actualizar_disponibilidades
from model.utils import etapa_registrada, guardar_registro_csv, guardar_registro_sqlite, obtener_siguiente_iteracion
from pyomo.util.infeasible import log_infeasible_constraints
from pyomo.opt import TerminationCondition as tc_enum


REPORTE_PATH = Path(__file__).resolve().parents[1] / "results" / "reporte_cbc.csv"
REPORTE_PATH.parent.mkdir(parents=True, exist_ok=True)


def resolver_modelo_cbc(modelo, datos, permutacion):
    """
    Resuelve un ConcreteModel de Pyomo con CBC,
    guarda métricas y solución en CSVs.

    Args:
        modelo: instancia de ConcreteModel construida.
        datos: estructura de datos para actualizar.
        permutacion: lista de semestres procesados.

    Returns:
        datos_act: datos actualizados tras la solución.
        obj_val: float con valor de la función objetivo.
    """
    iteracion_actual = obtener_siguiente_iteracion()
    registros = []

    with etapa_registrada("Optimización CBC", iteracion_actual, modelo=modelo, version="constructor_decorador",
                          registros=registros, semestre=permutacion[-1], permutacion=permutacion):
        opt = SolverFactory('cbc')
        opt.options['seconds'] = 3600
        opt.options['ratioGap'] = 0.0
        results = opt.solve(modelo, tee=True)

    sc = results.solver.status
    tc = results.solver.termination_condition
    print(f"Solver status={sc}, termination={tc}")

    aceptables = {tc_enum.optimal, tc_enum.feasible, tc_enum.maxTimeLimit}

    if tc == tc_enum.infeasible:
        print("❌ Modelo infactible.")
        diag_path = Path(__file__).resolve().parents[1] / "results" / "diagnosticos"
        diag_path.mkdir(parents=True, exist_ok=True)
        with open(diag_path / f"diagnostico_cbc_{permutacion[-1]}.txt", "w") as f:
            logging_logger = logging.getLogger(f"diagnostico_cbc_{permutacion[-1]}")
            logging_logger.setLevel(logging.DEBUG)
            ch = logging.StreamHandler(f)
            ch.setLevel(logging.DEBUG)
            logging_logger.addHandler(ch)
            log_infeasible_constraints(modelo, log_expression=True,
                                       log_variables=True, logger=logging_logger)
        registros[-1]["soluciones_factibles"] = 0
        guardar_registro_csv(registros, REPORTE_PATH)
        guardar_registro_sqlite(registros)
        return None, None

    elif tc not in aceptables:
        raise RuntimeError(f"Solver falló: condition={tc}")

    print(f"✔️ Solver aceptado: {tc}")
    registros[-1]["soluciones_factibles"] = 1

    sol_dict = {}
    for v in modelo.component_data_objects(Var, active=True, descend_into=True):
        val = getattr(v, "value", None)
        if val is None:
            continue
        if abs(val) > 1e-6:
            sol_dict[v.name] = float(val)

    sol_dir = Path(__file__).resolve().parents[1] / "results" / "solutions"
    sol_dir.mkdir(parents=True, exist_ok=True)
    rama = "-".join(str(a) for a in permutacion)
    sol_csv = sol_dir / f"Solucion_CBC_{rama}.csv"
    pd.DataFrame.from_dict(sol_dict, orient="index", columns=["Valor"]).to_csv(sol_csv)
    print(f"✅ Solución CBC guardada en {sol_csv}")

    datos_act = actualizar_disponibilidades(sol_dict, copy.deepcopy(datos))

    try:
        obj_comp = next(modelo.component_data_objects(Objective, descend_into=True))
        obj_val = value(obj_comp)
    except StopIteration:
        obj_val = None

    guardar_registro_csv(registros, REPORTE_PATH)
    guardar_registro_sqlite(registros)

    return datos_act, obj_val
