import pandas as pd
import sqlite3
import itertools
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "anonymized" / "modelo_base.db"


def _read_sql(tabla: str, conn: sqlite3.Connection) -> pd.DataFrame:
    try:
        return pd.read_sql(f"SELECT * FROM {tabla}", conn)
    except Exception as exc:
        raise RuntimeError(f"Error leyendo la tabla '{tabla}': {exc}")


def cargar_datos() -> dict:
    dias  = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
    horas = list(range(7, 21))

    with sqlite3.connect(DB_PATH) as conn:
        df_profesores          = _read_sql("Profesores",          conn)
        df_profesores_disp     = _read_sql("Disponibilidad",      conn)
        df_materias            = _read_sql("Materias",            conn)
        df_materias_profesores = _read_sql("Materias_Profesores", conn)
        df_aulas               = _read_sql("Aulas",               conn)
        df_grupos              = _read_sql("Grupos",              conn)
        df_materias_grupos     = _read_sql("Materias_Grupos",     conn)
        df_turnos_horas        = _read_sql("Turnos_Horas_Dias",   conn)
        df_dias_preferencias   = _read_sql("Dias_Preferencias",   conn)

    df_turnos_grupos = df_turnos_horas.merge(df_grupos, on="Turno")
    df_materias_dias = df_dias_preferencias.merge(df_materias, on="Preferencia")

    combinaciones = itertools.product(dias, horas, df_aulas["id"])
    df_aulas_disp = pd.DataFrame(combinaciones, columns=["DIA", "HORA", "ID_AULA"])
    df_aulas_disp["DISPONIBLE"] = 1

    combinaciones_bin = itertools.product(df_profesores["id"], dias, horas)
    df_profesores_disp_bin = pd.DataFrame(combinaciones_bin, columns=["ID_PROFESOR", "DIA", "HORA"])
    df_profesores_disp_bin["DISPONIBLE"] = 1

    return {
        "df_profesores":            df_profesores,
        "df_profesores_disponibles": df_profesores_disp,
        "df_profesores_disp_bin":   df_profesores_disp_bin,
        "df_materias":              df_materias,
        "df_materias_profesores":   df_materias_profesores,
        "df_aulas":                 df_aulas,
        "df_grupos":                df_grupos,
        "df_materias_grupos":       df_materias_grupos,
        "df_turnos_horas":          df_turnos_horas,
        "df_turnos_grupos":         df_turnos_grupos,
        "df_dias_preferencias":     df_dias_preferencias,
        "df_materias_dias":         df_materias_dias,
        "df_aulas_disponibles":     df_aulas_disp,
    }
