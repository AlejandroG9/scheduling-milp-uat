# solvers/gurobi.py

import time
from pyomo.opt import SolverFactory
from solvers._base import procesar_resultado

TIME_LIMIT = 3600


def resolver_modelo_gurobi(modelo, datos, permutacion):
    semestre = permutacion[-1]
    opt = SolverFactory('gurobi')
    opt.options['TimeLimit']    = TIME_LIMIT
    opt.options['SoftMemLimit'] = 30720

    t0 = time.time()
    results = opt.solve(modelo, tee=True)
    tiempo  = time.time() - t0

    datos_act, obj_val, status, sol_dict, _ = procesar_resultado(
        modelo, datos, results, "gurobi", semestre, permutacion
    )
    return datos_act, obj_val, status, tiempo
