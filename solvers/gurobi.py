# optim/solvers/gurobi.py

from pathlib import Path
import copy
import os
import time
import pandas as pd
import logging
import psutil
from pyomo.opt import SolverFactory
from pyomo.environ import Var, Objective, value
from model.update_data import actualizar_disponibilidades
from model.utils import etapa_registrada, guardar_registro_csv, guardar_registro_sqlite, obtener_siguiente_iteracion, exportar_iis_gurobi
from pyomo.util.infeasible import log_infeasible_constraints
from pyomo.opt import TerminationCondition as tc_enum



# ————————————————————————————
# Configuración del reporte global
# ————————————————————————————
REPORTE_PATH = Path(__file__).resolve().parents[1] / "results" / "reporte_pyomo_modelo_nuevo.csv"
REPORTE_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_pyomo_infeasible_constraints(modelo):
    # Create a logger object with DEBUG level
    logging_logger = logging.getLogger()
    logging_logger.setLevel(logging.DEBUG)
    # Create a console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # add the handler to the logger
    logging_logger.addHandler(ch)
    # Log the infeasible constraints of pyomo object
    print("\n🔍 Diagnóstico: Mostrando restricciones infactibles...")
    log_infeasible_constraints(modelo, log_expression=True,
                         log_variables=True, logger=logging_logger)






def resolver_modelo_gurobi(modelo, datos, permutacion):
    """
    Resuelve un ConcreteModel de Pyomo con Gurobi,
    guarda métricas y solución en CSVs.

    Args:
        modelo: instancia de ConcreteModel construida.
        datos: estructura de datos para actualizar.
        permutacion: lista de semestres procesados.

    Returns:
        sol_dict: Dict[str, float] con valores de variables.
        datos_act: datos actualizados tras la solución.
        obj_val: float con valor de la función objetivo.
    """
    # Verifica si ya existe el archivo para saber el número de iteración
    iteracion_actual = obtener_siguiente_iteracion()
    versio_modelo = "constructor_decorador"
    registros = []

    with etapa_registrada("Optimización Gurobi", iteracion_actual, modelo=modelo, version="constructor_decorador",
                          registros=registros, semestre=permutacion[-1], permutacion=permutacion):
        opt = SolverFactory('gurobi')
        opt.options["SoftMemLimit"] = 30720  # si estás usando Gurobi >= 10
        opt.options['TimeLimit'] = 3600
        results = opt.solve(modelo, tee=True)#, load_solutions=False)  # 👈 clave: no cargar soluciones

    sc = results.solver.status
    tc = results.solver.termination_condition
    print(f"Solver status={sc}, termination={tc}")

    aceptables = {tc_enum.optimal, tc_enum.feasible, tc_enum.maxTimeLimit}

    # Diagnóstico en caso de infactibilidad
    if tc == tc_enum.infeasible:
        print("❌ Modelo infactible. Ejecutando diagnóstico...\n")
        diag_path = Path(__file__).resolve().parents[1] / "results" / "diagnosticos"
        diag_path.mkdir(parents=True, exist_ok=True)

        with open(diag_path / f"diagnostico_{permutacion[-1]}.txt", "w") as f:
            logging_logger = logging.getLogger(f"diagnostico_{permutacion[-1]}")
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

    # Si llegamos aquí, sí hay solución aceptable
    print(f"✔️ Solver aceptado: {tc} ({results.solver.message})")
    registros[-1]["soluciones_factibles"] = 1

    # — Etapa 2: Extracción de solución —
    sol_dict = {}
    for v in modelo.component_data_objects(Var, active=True, descend_into=True):
        val = getattr(v, "value", None)
        if val is None:
            continue
        if abs(val) > 1e-6:
            sol_dict[v.name] = float(val)

    # Guardar CSV de la solución
    sol_dir = Path(__file__).resolve().parents[1] / "results" / "solutions"
    sol_dir.mkdir(parents=True, exist_ok=True)
    rama = "-".join(str(a) for a in permutacion)
    sol_csv = sol_dir / f"Solucion_Modelo_{rama}.csv"
    pd.DataFrame.from_dict(sol_dict, orient="index", columns=["Valor"])\
      .to_csv(sol_csv)
    print(f"✅ Solución guardada en {sol_csv}")

    # Actualizar datos para la siguiente iteración
    datos_act = actualizar_disponibilidades(sol_dict, copy.deepcopy(datos))

    # — Etapa 3: Valor objetivo —
    try:
        obj_comp = next(
            modelo.component_data_objects(Objective, descend_into=True)
        )
        obj_val = value(obj_comp)
    except StopIteration:
        obj_val = None


    guardar_registro_csv(registros, REPORTE_PATH)
    guardar_registro_sqlite(registros)

    return datos_act, obj_val