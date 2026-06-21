# solvers/highs.py
# Requiere: pip install highspy

import time
from pyomo.opt import SolverFactory
from solvers._base import procesar_resultado

TIME_LIMIT = 3600


def resolver_modelo_highs(modelo, datos, permutacion):
    semestre = permutacion[-1]
    opt = SolverFactory('appsi_highs')
    opt.options['time_limit']   = float(TIME_LIMIT)
    opt.options['mip_rel_gap']  = 0.0

    t0 = time.time()
    results = opt.solve(modelo, tee=True)
    tiempo  = time.time() - t0

    datos_act, obj_val, status, sol_dict, _ = procesar_resultado(
        modelo, datos, results, "highs", semestre, permutacion
    )
    return datos_act, obj_val, status, tiempo
