"""
monitor/dashboard.py — Monitor de experimentos en tiempo real

Uso:
    .venv/bin/streamlit run monitor/dashboard.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT    = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "results" / "experiments.db"
SOL_DIR = ROOT / "results" / "solutions"

sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="Monitor — scheduling-milp-uat",
    page_icon="📅",
    layout="wide",
)

# ── Paleta de colores para materias ──────────────────────────────────────────
PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
    "#d4a6c8", "#86bcb6", "#f1ce63", "#a0cbe8", "#ffbe7d",
    "#8cd17d", "#b6992d", "#499894", "#e15759", "#79706e",
]

DIAS  = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
HORAS = list(range(7, 21))

# ── Helpers ───────────────────────────────────────────────────────────────────

def color_for(materia: str, color_map: dict) -> str:
    if materia not in color_map:
        color_map[materia] = PALETTE[len(color_map) % len(PALETTE)]
    return color_map[materia]


def leer_solucion(csv_path: Path) -> pd.DataFrame:
    """Parsea el CSV de solución y devuelve un DataFrame con columnas limpias."""
    df_raw = pd.read_csv(csv_path, index_col=0)
    filas  = []
    for var_name in df_raw.index:
        if not var_name.startswith("x["):
            continue
        interior = var_name[2:-1]
        partes   = interior.split(",")
        if len(partes) < 6:
            continue
        filas.append({
            "Profesor": partes[0].strip(),
            "Materia":  partes[1].strip(),
            "Dia":      partes[2].strip(),
            "Hora":     int(partes[3].strip()),
            "Aula":     partes[4].strip(),
            "Grupo":    partes[5].strip(),
        })
    return pd.DataFrame(filas)


def horario_html(df_grupo: pd.DataFrame, color_map: dict) -> str:
    """Genera una tabla HTML coloreada para un grupo."""
    # Construir dict {(dia, hora): lista de celdas}
    grid: dict[tuple, list] = {}
    for _, row in df_grupo.iterrows():
        key = (row["Dia"], row["Hora"])
        grid.setdefault(key, []).append(row)

    th_style = (
        "background:#1e293b; color:#f1f5f9; padding:8px 14px; "
        "text-align:center; font-size:13px; border:1px solid #334155;"
    )
    hora_style = (
        "background:#0f172a; color:#94a3b8; padding:6px 10px; "
        "text-align:center; font-size:12px; border:1px solid #1e293b; "
        "font-weight:bold; white-space:nowrap;"
    )
    td_empty = (
        "background:#0f172a; border:1px solid #1e293b; "
        "min-width:130px; height:58px;"
    )

    html = ['<table style="border-collapse:collapse; width:100%; font-family:sans-serif;">']

    # Encabezado
    html.append("<thead><tr>")
    html.append(f'<th style="{th_style}">Hora</th>')
    for dia in DIAS:
        html.append(f'<th style="{th_style}">{dia}</th>')
    html.append("</tr></thead><tbody>")

    for hora in HORAS:
        html.append("<tr>")
        html.append(f'<td style="{hora_style}">{hora}:00</td>')
        for dia in DIAS:
            celdas = grid.get((dia, hora), [])
            if not celdas:
                html.append(f'<td style="{td_empty}"></td>')
            else:
                # Puede haber varias materias a la misma hora/día (aunque no debería)
                partes_html = []
                for c in celdas:
                    bg    = color_for(c["Materia"], color_map)
                    texto = (
                        f'<div style="'
                        f'background:{bg}; color:#fff; border-radius:6px; '
                        f'padding:5px 8px; margin:2px; font-size:11px; '
                        f'line-height:1.4;">'
                        f'<b>{c["Materia"]}</b><br>'
                        f'{c["Profesor"]}<br>'
                        f'<span style="opacity:.8">{c["Aula"]}</span>'
                        f'</div>'
                    )
                    partes_html.append(texto)
                td_style = "border:1px solid #1e293b; padding:2px; background:#0f172a; vertical-align:top;"
                html.append(f'<td style="{td_style}">{"".join(partes_html)}</td>')
        html.append("</tr>")

    html.append("</tbody></table>")
    return "".join(html)


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("📅 Monitor de Experimentos — scheduling-milp-uat")
st.caption("Lee `results/experiments.db` · actualiza con el botón o activa auto-refresh")

col_btn, col_tog = st.columns([1, 3])
with col_btn:
    st.button("🔄 Actualizar")
with col_tog:
    auto = st.toggle("Auto-refresh 5 s", value=False)

if auto:
    st.markdown("<meta http-equiv='refresh' content='5'>", unsafe_allow_html=True)

st.divider()

# ── Datos de runs ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=5)
def cargar_runs() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        try:
            return pd.read_sql("SELECT * FROM runs ORDER BY id DESC", conn)
        except Exception:
            return pd.DataFrame()


df = cargar_runs()

tab_runs, tab_horario = st.tabs(["📊 Corridas", "🗓️ Horarios"])

# ═══════════════════════════════════════════════════════
# TAB 1 — Corridas
# ═══════════════════════════════════════════════════════
with tab_runs:
    if df.empty:
        st.warning(
            "No hay datos todavía. Ejecuta:\n"
            "```\n.venv/bin/python runners/smoke_test.py\n```"
        )
    else:
        # Sidebar‑style filters inside tab
        with st.expander("Filtros", expanded=False):
            fc1, fc2, fc3 = st.columns(3)
            exp_opts = ["Todos"] + sorted(df["experiment"].dropna().unique().tolist())
            exp_sel  = fc1.selectbox("Experimento", exp_opts, key="exp_f")
            sol_opts = ["Todos"] + sorted(df["solver"].dropna().unique().tolist())
            sol_sel  = fc2.selectbox("Solver", sol_opts, key="sol_f")
            sem_opts = ["Todos"] + sorted(df["semestre"].dropna().astype(int).unique().tolist())
            sem_sel  = fc3.selectbox("Semestre", sem_opts, key="sem_f")

        df_f = df.copy()
        if exp_sel != "Todos":
            df_f = df_f[df_f["experiment"] == exp_sel]
        if sol_sel != "Todos":
            df_f = df_f[df_f["solver"] == sol_sel]
        if sem_sel != "Todos":
            df_f = df_f[df_f["semestre"] == int(sem_sel)]

        # Tarjetas
        total    = len(df_f)
        optimal  = (df_f["status"] == "optimal").sum()
        feasible = (df_f["status"] == "feasible").sum()
        timeouts = (df_f["status"] == "timeout").sum()
        errors   = df_f["status"].isin(["infeasible", "error"]).sum()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Runs",      total)
        c2.metric("Óptimos",   optimal,  f"{100*optimal/total:.0f}%" if total else None)
        c3.metric("Factibles", feasible)
        c4.metric("Timeouts",  timeouts)
        c5.metric("Errores",   errors)

        # Gráfica
        if "tiempo_solver_s" in df_f.columns and df_f["tiempo_solver_s"].notna().any():
            COLOR_MAP = {
                "optimal":    "#2ecc71",
                "feasible":   "#f1c40f",
                "timeout":    "#e67e22",
                "infeasible": "#e74c3c",
                "error":      "#95a5a6",
            }
            fig = px.strip(
                df_f.dropna(subset=["tiempo_solver_s"]),
                x="semestre", y="tiempo_solver_s",
                color="status", facet_col="solver",
                hover_data=["id", "replica", "obj_val", "fecha", "notas"],
                color_discrete_map=COLOR_MAP,
                labels={"tiempo_solver_s": "Tiempo (s)", "semestre": "Semestre"},
                title="Tiempo del solver por semestre",
            )
            fig.update_layout(height=340, margin=dict(t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        # Tabla
        cols_show = ["id", "fecha", "experiment", "solver", "semestre", "replica",
                     "status", "obj_val", "tiempo_solver_s", "n_variables",
                     "n_restricciones", "notas"]
        cols_disp = [c for c in cols_show if c in df_f.columns]
        st.dataframe(
            df_f[cols_disp].head(200),
            use_container_width=True,
            column_config={
                "obj_val":         st.column_config.NumberColumn("Obj. val",    format="%.2f"),
                "tiempo_solver_s": st.column_config.NumberColumn("Tiempo (s)",  format="%.1f"),
                "n_variables":     st.column_config.NumberColumn("Variables"),
                "n_restricciones": st.column_config.NumberColumn("Restricciones"),
            },
        )

# ═══════════════════════════════════════════════════════
# TAB 2 — Horarios
# ═══════════════════════════════════════════════════════
with tab_horario:
    if not SOL_DIR.exists() or not list(SOL_DIR.glob("*.csv")):
        st.info(
            "No hay soluciones todavía.\n"
            "Ejecuta: `.venv/bin/python runners/smoke_test.py`"
        )
    else:
        csvs    = sorted(SOL_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        sel_csv = st.selectbox(
            "Archivo de solución",
            [p.name for p in csvs],
            key="csv_sel",
        )
        df_sol = leer_solucion(SOL_DIR / sel_csv)

        if df_sol.empty:
            st.warning("No se encontraron variables x[...] activas en el archivo.")
        else:
            grupos = sorted(df_sol["Grupo"].unique())
            materias_all = sorted(df_sol["Materia"].unique())

            # Leyenda de colores
            color_map: dict[str, str] = {}
            for m in materias_all:
                color_for(m, color_map)

            st.markdown("**Leyenda de materias**")
            leg_cols = st.columns(min(len(materias_all), 5))
            for i, mat in enumerate(materias_all):
                col = leg_cols[i % len(leg_cols)]
                col.markdown(
                    f'<span style="background:{color_map[mat]};color:#fff;'
                    f'padding:3px 10px;border-radius:4px;font-size:12px;">'
                    f'{mat}</span>',
                    unsafe_allow_html=True,
                )

            st.divider()

            # Vista: un grupo o todos
            vista = st.radio(
                "Vista",
                ["Por grupo", "Todos los grupos (columnas separadas)"],
                horizontal=True,
            )

            if vista == "Por grupo":
                grupo_sel = st.selectbox("Grupo", grupos, key="grp_sel")
                df_g = df_sol[df_sol["Grupo"] == grupo_sel]
                st.markdown(
                    f"**Grupo {grupo_sel}** — {len(df_g)} bloques asignados",
                    unsafe_allow_html=True,
                )
                st.markdown(horario_html(df_g, color_map), unsafe_allow_html=True)

            else:
                # Mostrar todos los grupos uno debajo del otro
                for grupo in grupos:
                    df_g = df_sol[df_sol["Grupo"] == grupo]
                    with st.expander(f"Grupo {grupo}  ({len(df_g)} bloques)", expanded=True):
                        st.markdown(horario_html(df_g, color_map), unsafe_allow_html=True)

            st.divider()

            # Estadísticas rápidas
            st.markdown("**Estadísticas de la solución**")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Bloques totales",   len(df_sol))
            s2.metric("Materias únicas",   df_sol["Materia"].nunique())
            s3.metric("Profesores únicos", df_sol["Profesor"].nunique())
            s4.metric("Grupos",            df_sol["Grupo"].nunique())

            with st.expander("Tabla detallada de la solución"):
                st.dataframe(df_sol, use_container_width=True)
