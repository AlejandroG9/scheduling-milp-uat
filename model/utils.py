from contextlib import contextmanager
import time
import psutil
import logging
import pyomo.environ as pyo
from pathlib import Path
import pandas as pd
import os
import sqlite3

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = RESULTS_DIR / "experiments.db"
TABLA   = "reporte_iteraciones"


def get_system_metrics():
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'ram_percent': psutil.virtual_memory().percent,
        'num_cores':   psutil.cpu_count(logical=False),
        'num_threads': psutil.cpu_count(logical=True),
    }


def contar_restricciones(modelo, nombres):
    return {
        nombre: len(getattr(modelo, nombre)) if hasattr(modelo, nombre) else None
        for nombre in nombres
    }


@contextmanager
def etapa_registrada(nombre_etapa, iteracion, modelo=None, version=None,
                     registros=None, semestre=None, permutacion=None):
    inicio = time.time()
    yield
    fin = time.time()
    metrics = get_system_metrics()

    restricciones_a_contar = [
        'restriccion_hora_ocupada', 'restriccion_aux_hueco',
        'restriccion_huecos_forzar_1', 'restriccion_huecos_forzar_2', 'restriccion_huecos_forzar_3',
        'restriccion_clases_consecutivas', 'restriccion_horas_antes', 'restriccion_horas_despues',
        'producto_de_preferencias', 'restriccion_xy', 'restriccion_disponibilidad',
        'restriccion_disponibilidad_aula', 'restriccion_xu', 'restriccion_horas_maximas',
        'restriccion_horas_materia', 'restriccion_horas_continuas', 'restriccion_xv',
        'restriccion_misma_hora', 'restriccion_xq', 'restriccion_mismo_dia',
        'restriccion_aulas_laboratorios', 'restrcciones_disjutivas',
        'restriccion_clases_consecutivas_laboratorio', 'restriccion_unicidad_profesores',
        'restriccion_unicidad_materias_grupo_semestres', 'restriccion_unicidad_aulas',
    ]

    registro = {
        'iteracion':         iteracion,
        'semestre':          semestre,
        'rama':              '-'.join(str(x) for x in permutacion) if isinstance(permutacion, list) else permutacion,
        'etapa':             nombre_etapa,
        'tiempo_segundos':   fin - inicio,
        **metrics,
        'PROFESORES':   len(modelo.PROFESORES)   if hasattr(modelo, 'PROFESORES')   else None,
        'MATERIAS':     len(modelo.MATERIAS)     if hasattr(modelo, 'MATERIAS')     else None,
        'MATERIAS_SEM': len(modelo.MATERIAS_SEM) if hasattr(modelo, 'MATERIAS_SEM') else None,
        'MATERIAS_FIN': len(modelo.MATERIAS_FIN) if hasattr(modelo, 'MATERIAS_FIN') else None,
        'MATERIAS_VAR': len(modelo.MATERIAS_VAR) if hasattr(modelo, 'MATERIAS_VAR') else None,
        'MATERIAS_LAB': len(modelo.MATERIAS_LAB) if hasattr(modelo, 'MATERIAS_LAB') else None,
        'DIAS':         len(modelo.DIAS)         if hasattr(modelo, 'DIAS')         else None,
        'HORAS':        len(modelo.HORAS)        if hasattr(modelo, 'HORAS')        else None,
        'AULAS':        len(modelo.AULAS)        if hasattr(modelo, 'AULAS')        else None,
        'AULAS_LAB':    len(modelo.AULAS_LAB)    if hasattr(modelo, 'AULAS_LAB')    else None,
        'GRUPOS':       len(modelo.GRUPOS)       if hasattr(modelo, 'GRUPOS')       else None,
        'x': len(modelo.x) if hasattr(modelo, 'x') else None,
        'r': len(modelo.r) if hasattr(modelo, 'r') else None,
        'z': len(modelo.z) if hasattr(modelo, 'z') else None,
        'w': len(modelo.w) if hasattr(modelo, 'w') else None,
        'k': len(modelo.k) if hasattr(modelo, 'k') else None,
        's': len(modelo.s) if hasattr(modelo, 's') else None,
        't': len(modelo.t) if hasattr(modelo, 't') else None,
        'v': len(modelo.v) if hasattr(modelo, 'v') else None,
        'q': len(modelo.q) if hasattr(modelo, 'q') else None,
        'soluciones_factibles': None,
        'version_del_modelo':   version,
        'huecos_grupos':  True if hasattr(modelo, 'z') else False,
        'preferencias':   True if hasattr(modelo, 'r') else False,
        'huecos_prof':    True if hasattr(modelo, 'e') else False,
    }

    registro.update(contar_restricciones(modelo, restricciones_a_contar))

    if registros is not None:
        registros.append(registro)


def guardar_registro_csv(registros, archivo_csv):
    df_nuevo = pd.DataFrame(registros)
    if os.path.exists(archivo_csv):
        df_completo = pd.concat([pd.read_csv(archivo_csv), df_nuevo], ignore_index=True)
    else:
        df_completo = df_nuevo
    df_completo.to_csv(archivo_csv, index=False)


def guardar_registro_sqlite(registros, db_path=DB_PATH, tabla=TABLA):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    df_nuevo = pd.DataFrame(registros)
    with sqlite3.connect(db_path) as conn:
        df_nuevo.to_sql(tabla, conn, if_exists='append', index=False)


def obtener_siguiente_iteracion(db_path=DB_PATH, tabla=TABLA):
    db_path = Path(db_path)
    if not db_path.exists():
        return 1
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT MAX(iteracion) FROM {tabla}")
            resultado = cur.fetchone()
            return (resultado[0] or 0) + 1
    except sqlite3.Error:
        return 1


EXPERIMENTS_DB = RESULTS_DIR / "experiments.db"


def registrar_run(experiment, solver, semestre, replica,
                  status, obj_val, tiempo_solver_s,
                  modelo=None, release_id="v1",
                  huecos_grupo=True, huecos_prof=False,
                  preferencias=True, disjuntives=False,
                  peso_tn=None, peso_md=None, peso_ags=None,
                  notas=None):
    """
    Escribe una fila en la tabla `runs` de experiments.db.
    Llamar desde los runners después de cada ejecución del solver.
    """
    metrics = get_system_metrics()

    n_vars   = None
    n_restrs = None
    if modelo is not None:
        try:
            n_vars   = sum(1 for _ in modelo.component_data_objects(
                               __import__('pyomo.environ', fromlist=['Var']).Var,
                               active=True, descend_into=True))
            n_restrs = sum(1 for _ in modelo.component_data_objects(
                               __import__('pyomo.environ', fromlist=['Constraint']).Constraint,
                               active=True, descend_into=True))
        except Exception:
            pass

    row = {
        "experiment":      experiment,
        "release_id":      release_id,
        "solver":          solver,
        "semestre":        semestre,
        "permutacion":     str(semestre),
        "huecos_grupo":    int(huecos_grupo),
        "huecos_prof":     int(huecos_prof),
        "preferencias":    int(preferencias),
        "disjuntives":     int(disjuntives),
        "peso_tn":         peso_tn,
        "peso_md":         peso_md,
        "peso_ags":        peso_ags,
        "status":          status,
        "obj_val":         obj_val,
        "tiempo_total_s":  tiempo_solver_s,
        "tiempo_solver_s": tiempo_solver_s,
        "cpu_percent":     metrics["cpu_percent"],
        "ram_percent":     metrics["ram_percent"],
        "n_variables":     n_vars,
        "n_restricciones": n_restrs,
        "modelo_version":  "1.0",
        "notas":           notas,
    }

    EXPERIMENTS_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(EXPERIMENTS_DB) as conn:
        pd.DataFrame([row]).to_sql("runs", conn, if_exists="append", index=False)

    print(f"[DB] run registrado — {experiment}/{solver}/sem{semestre}/rep{replica} → {status} obj={obj_val}")
