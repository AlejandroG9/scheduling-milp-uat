"""
analysis/generate_tables.py
Reads experiments.db and writes LaTeX table files for E1, E2, and E3.

Usage:
    python analysis/generate_tables.py [--db results/experiments.db] [--out <dir>]

Output files (written to --out directory, default: tablas/):
    e1_resultados.tex
    e2_benchmark.tex
    e3_sensibilidad.tex
"""

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


# ─── helpers ────────────────────────────────────────────────────────────────

def load_runs(db_path: Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql("SELECT * FROM runs", conn)
    return df


def fmt(mean, std, decimals=1):
    """Format mean ± std with consistent decimals."""
    return f"${mean:.{decimals}f} \\pm {std:.{decimals}f}$"


def fmt_time(mean, std):
    """Format time as mean ± std, auto-select decimals."""
    decimals = 0 if mean >= 10 else 1
    return fmt(mean, std, decimals)


def status_label(df_group):
    """Return 'Optimal' if all runs are optimal, else 'Feasible'."""
    if (df_group["status"] == "optimal").all():
        return "Optimal"
    opt_pct = (df_group["status"] == "optimal").mean() * 100
    return f"Feas. ({opt_pct:.0f}\\% opt)"


# ─── E1 ─────────────────────────────────────────────────────────────────────

SEM_META = {
    1: (19, 8, 5), 2: (13, 11, 2), 3: (16, 8, 4),
    4: (16, 9, 2), 5: (20, 8, 4), 6: (13, 8, 2),
    7: (17, 8, 4), 8: (12, 8, 3), 9: (11, 6, 2),
}

def make_e1(df: pd.DataFrame, out_dir: Path):
    e1 = df[df["experiment"] == "full"].copy()
    if e1.empty:
        print("  [E1] No data found — writing placeholder table.")
        return

    rows = []
    for sem in range(1, 10):
        g = e1[e1["semestre"] == sem]
        if g.empty:
            rows.append(f"  {sem} & -- & -- & -- & -- & -- & -- & -- / -- \\\\")
            continue
        profs, courses, groups = SEM_META[sem]
        status = status_label(g)
        obj_m, obj_s = g["obj_val"].mean(), g["obj_val"].std()
        t_m, t_s = g["tiempo_solver_s"].mean(), g["tiempo_solver_s"].std()
        t_min, t_max = g["tiempo_solver_s"].min(), g["tiempo_solver_s"].max()
        rows.append(
            f"  {sem} & {profs} & {courses} & {groups} & {status} & "
            f"{fmt(obj_m, obj_s)} & {fmt_time(t_m, t_s)} & "
            f"{t_min:.0f} / {t_max:.0f} \\\\"
        )

    # summary row
    obj_m, obj_s = e1["obj_val"].mean(), e1["obj_val"].std()
    t_m, t_s = e1["tiempo_solver_s"].mean(), e1["tiempo_solver_s"].std()
    t_min, t_max = e1["tiempo_solver_s"].min(), e1["tiempo_solver_s"].max()
    summary = (
        f"  \\textbf{{All}} & -- & -- & -- & {status_label(e1)} & "
        f"{fmt(obj_m, obj_s)} & {fmt_time(t_m, t_s)} & "
        f"{t_min:.0f} / {t_max:.0f} \\\\"
    )

    body = "\n".join(rows)
    table = rf"""\begin{{table}}[htbp]
\centering
\caption{{E1 --- Solution quality and computation times across nine semester instances (10 replications each, Gurobi).}}
\label{{tab:e1_resultados}}
\scriptsize
\begin{{tabular}}{{rcccrrrr}}
\toprule
\textbf{{Sem.}} & \textbf{{Profs.}} & \textbf{{Courses}} & \textbf{{Groups}}
  & \textbf{{Status}} & \textbf{{Obj.\ (mean$\pm$std)}} & \textbf{{Time (s) mean$\pm$std}} & \textbf{{Min / Max (s)}} \\
\midrule
{body}
\midrule
{summary}
\botrule
\end{{tabular}}
\begin{{tablenotes}}
\small
\item Status: \textit{{Optimal}} = proven optimal within time limit; \textit{{Feasible}} = best feasible solution found before time limit.
\item Obj.\ value = total weighted gap and preference penalty (lower is better).
\end{{tablenotes}}
\end{{table}}
"""
    (out_dir / "e1_resultados.tex").write_text(table)
    print("  [E1] Written e1_resultados.tex")


# ─── E2 ─────────────────────────────────────────────────────────────────────

SOLVERS = ["gurobi", "highs", "cbc", "glpk"]
SOLVER_LABELS = {"gurobi": "Gurobi", "highs": "HiGHS", "cbc": "CBC", "glpk": "GLPK"}
BENCH_SEMS = {1: "S1 (large)", 3: "S3 (medium)", 9: "S9 (small)"}

def make_e2(df: pd.DataFrame, out_dir: Path):
    e2 = df[df["experiment"] == "benchmark"].copy()
    if e2.empty:
        print("  [E2] No data found — writing placeholder table.")
        return

    blocks = []
    for sem, sem_label in BENCH_SEMS.items():
        solver_rows = []
        for i, solver in enumerate(SOLVERS):
            g = e2[(e2["semestre"] == sem) & (e2["solver"] == solver)]
            label = f"\\multirow{{4}}{{*}}{{{sem_label}}}" if i == 0 else ""
            if g.empty:
                solver_rows.append(f"  {label} & {SOLVER_LABELS[solver]} & -- & -- & -- & -- & -- \\\\")
                continue
            status = status_label(g)
            opt_pct = (g["status"] == "optimal").mean() * 100
            t_m, t_s = g["tiempo_solver_s"].mean(), g["tiempo_solver_s"].std()
            obj_m = g["obj_val"].mean()
            solver_rows.append(
                f"  {label} & {SOLVER_LABELS[solver]} & {status} & "
                f"{t_m:.1f} & {t_s:.1f} & {obj_m:.1f} & {opt_pct:.0f} \\\\"
            )
        blocks.append("\n".join(solver_rows))

    body = "\n\\midrule\n".join(blocks)
    table = rf"""\begin{{table}}[htbp]
\centering
\caption{{E2 --- Solver benchmark on three representative instances (5 replications each). Time limit: 3\,600\,s.}}
\label{{tab:e2_benchmark}}
\scriptsize
\begin{{tabular}}{{llcrrrr}}
\toprule
\textbf{{Instance}} & \textbf{{Solver}} & \textbf{{Status}}
  & \textbf{{Time (s) mean}} & \textbf{{Std (s)}} & \textbf{{Obj.\ mean}} & \textbf{{Opt.\ rate (\%)}} \\
\midrule
{body}
\botrule
\end{{tabular}}
\begin{{tablenotes}}
\small
\item Opt.\ rate = percentage of replications reaching proven optimality within the time limit.
\item All solvers use the same model configuration as E1 (huecos\_grupo=True, preferencias=True).
\end{{tablenotes}}
\end{{table}}
"""
    (out_dir / "e2_benchmark.tex").write_text(table)
    print("  [E2] Written e2_benchmark.tex")


# ─── E3 ─────────────────────────────────────────────────────────────────────

PARAM_LABELS = {
    "tn":  r"$tn$ (shift--hour)",
    "md":  r"$md$ (day preference)",
    "ags": r"$ags$ (classroom preference)",
}
FACTORS = [0.5, 2.0, 5.0]
WEIGHT_COLS = {"tn": "peso_tn", "md": "peso_md", "ags": "peso_ags"}

def make_e3(df: pd.DataFrame, out_dir: Path):
    e3 = df[df["experiment"] == "sensitivity"].copy()
    if e3.empty:
        print("  [E3] No data found — writing placeholder table.")
        return

    # baseline
    base = e3[(e3["peso_tn"] == 1.0) & (e3["peso_md"] == 1.0) & (e3["peso_ags"] == 1.0)]
    base_obj = base["obj_val"].mean() if not base.empty else None

    rows = []
    # baseline row
    if base_obj is not None:
        t_m, t_s = base["tiempo_solver_s"].mean(), base["tiempo_solver_s"].std()
        obj_s = base["obj_val"].std()
        rows.append(
            rf"  \multicolumn{{2}}{{l}}{{\textit{{Baseline}} ($tn=md=ags=1.0$)}} & "
            rf"{base_obj:.1f} & {obj_s:.1f} & 0 & {t_m:.1f} \\"
        )
    else:
        rows.append(
            r"  \multicolumn{2}{l}{\textit{Baseline} ($tn=md=ags=1.0$)} & -- & -- & 0 & -- \\"
        )

    for param, col in WEIGHT_COLS.items():
        rows.append(r"  \midrule")
        label = PARAM_LABELS[param]
        for i, factor in enumerate(FACTORS):
            other_cols = {v: 1.0 for k, v in WEIGHT_COLS.items() if k != param}
            mask = (e3[col] == factor)
            for oc, ov in other_cols.items():
                mask &= (e3[oc] == ov)
            g = e3[mask]

            multirow = f"\\multirow{{3}}{{*}}{{{label}}}" if i == 0 else ""
            if g.empty:
                rows.append(f"  {multirow} & {factor} & -- & -- & -- & -- \\\\")
                continue
            obj_m, obj_s = g["obj_val"].mean(), g["obj_val"].std()
            delta = ((obj_m - base_obj) / base_obj * 100) if base_obj else float("nan")
            t_m = g["tiempo_solver_s"].mean()
            rows.append(
                f"  {multirow} & {factor} & {obj_m:.1f} & {obj_s:.1f} & "
                f"{delta:+.1f} & {t_m:.1f} \\\\"
            )

    body = "\n".join(rows)
    table = rf"""\begin{{table}}[htbp]
\centering
\caption{{E3 --- Sensitivity of the objective function to preference weight scaling on Semester~9 (10 replications each, Gurobi).}}
\label{{tab:e3_sensibilidad}}
\scriptsize
\begin{{tabular}}{{llrrrr}}
\toprule
\textbf{{Parameter}} & \textbf{{Scale factor}} & \textbf{{Obj.\ mean}} & \textbf{{Obj.\ std}}
  & \textbf{{$\Delta$Obj (\%)}} & \textbf{{Time (s) mean}} \\
\midrule
{body}
\botrule
\end{{tabular}}
\begin{{tablenotes}}
\small
\item $\Delta$Obj (\%) = percentage change in mean objective value relative to the baseline.
\item One parameter is scaled at a time; the other two are held at $1.0$.
\item Lower objective value indicates fewer idle gaps and better preference satisfaction.
\end{{tablenotes}}
\end{{table}}
"""
    (out_dir / "e3_sensibilidad.tex").write_text(table)
    print("  [E3] Written e3_sensibilidad.tex")


# ─── main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate LaTeX result tables from experiments.db")
    parser.add_argument("--db",  default="results/experiments.db", help="Path to experiments.db")
    parser.add_argument("--out", default="tablas", help="Output directory for .tex files")
    args = parser.parse_args()

    db_path  = Path(args.db)
    out_dir  = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        print(f"DB not found at {db_path} — writing placeholder tables.")
        df = pd.DataFrame()
    else:
        df = load_runs(db_path)
        print(f"Loaded {len(df)} runs from {db_path}")

    make_e1(df, out_dir)
    make_e2(df, out_dir)
    make_e3(df, out_dir)
    print(f"\nDone. Tables written to {out_dir}/")


if __name__ == "__main__":
    main()
