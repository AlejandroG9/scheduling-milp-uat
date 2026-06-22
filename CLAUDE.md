# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexto

MILP de generación de horarios universitarios en Pyomo. Código asociado al artículo en revisión en *Mathematics* (MDPI), Manuscript ID: mathematics-3738359. Los resultados de los experimentos son los datos del paper — cualquier cambio que afecte reproducibilidad debe ser explícito.

## Flujo de trabajo obligatorio

```bash
# 1. Inicializar la base de resultados (solo una vez por máquina)
python scripts/init_db.py

# 2. Correr experimentos
python runners/smoke_test.py        # Validación rápida con solver libre
python runners/full_experiment.py   # E1: 9 semestres × réplicas, solo Gurobi
python runners/benchmark.py         # E2: comparación de solvers (S9/S3/S1)
python runners/sensitivity.py       # E3: sensibilidad de pesos tn, md, ags

# 3. Generar tablas LaTeX para el artículo
python analysis/generate_tables.py
```

`results/experiments.db` debe existir antes de cualquier runner — si falta, `registrar_run()` falla.

## Gotchas importantes

**Límites de tiempo distintos por solver** (definidos en cada módulo de `solvers/`, no en los runners):
- Gurobi: 3 600 s (1 h)
- HiGHS / CBC / GLPK: 1 800 s (30 min)

**Las soluciones se guardan en CSV, no en la BD**: a pesar de que `init_db.py` crea las tablas `solucion_x`, `solucion_w`, `solucion_r`, los valores de las variables se escriben como CSV en `results/solutions/Solucion_{solver}_sem{semestre}_{permutacion}.csv` (ver `solvers/_base.py::procesar_resultado()`).

**`sensitivity.py` muta el modelo en lugar de reconstruirlo**: `escalar_parametro()` modifica los valores de parámetros Pyomo directamente. Si se reutiliza un modelo, los factores se acumulan — siempre construir un modelo nuevo por réplica.

**`actualizar_disponibilidades()` modifica DataFrames en lugar**: al resolver semestres secuencialmente, `update_data.py` altera las disponibilidades de profesores y aulas en el dict `datos`. No asumir que `datos` es inmutable entre semestres.

**`registrar_run()` siempre guarda `permutacion=str(semestre)`** (línea 161 de `model/utils.py`), independientemente del valor real del parámetro `permutacion` pasado al modelo.

**`REPLICAS` en el código**: `full_experiment.py` tiene `REPLICAS = 10`; el README dice 30. El valor en el código es el que aplica.

## Parámetro `permutacion`

Lista de IDs de semestres que define el orden de procesamiento en solución secuencial. En los runners actuales siempre es `[semestre]` (un solo semestre). Controla qué aulas quedan bloqueadas por semestres procesados anteriormente en `builder.py`.

## Base de datos de resultados

`results/experiments.db` — SQLite. Tabla principal: `runs`.

Estados válidos en columna `status`: `"optimal"`, `"feasible"`, `"timeout"`, `"infeasible"`, `"error"`.

Columnas clave: `experiment`, `solver`, `semestre`, `replica`, `status`, `obj_val`, `tiempo_solver_s`, `peso_tn`, `peso_md`, `peso_ags`, `notas`.

## Convenciones de código

- **Idioma**: variables, comentarios y nombres de constraints en español; docstrings en inglés.
- **DataFrames**: prefijo `df_` (ej. `df_profesores`, `df_materias`).
- **Variables del modelo Pyomo**: letras simples (`modelo.x`, `modelo.w`, `modelo.z`, `modelo.r`).
- **snake_case** en todo lo demás.
- No hay linter ni formatter configurado.

## Python en este servidor

`python3` apunta a Python 3.14 (sistema). El proyecto usa **`python3.12`** (donde están instalados todos los paquetes). Siempre usar `python3.12` para correr experimentos.

## Correr experimentos sin perder el proceso (tmux)

El servidor no tiene monitor. Para que los experimentos sobrevivan si se cierra la conexión SSH:

```bash
# Crear sesión y lanzar experimento con log
tmux new-session -d -s exp_full
tmux send-keys -t exp_full \
  'export GUROBI_HOME=/opt/gurobi1203/linux64 PATH=$PATH:$GUROBI_HOME/bin LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$GUROBI_HOME/lib && python3.12 runners/full_experiment.py 2>&1 | tee logs/full.log' Enter

# Ver progreso desde Mac (reengancharse a la sesión)
tmux attach -t exp_full

# Desengancharse sin matar el proceso
# Ctrl+B, luego D
```

## Resiliencia — continuar desde donde se quedó

Todos los runners verifican la BD antes de cada réplica con `ya_ejecutado()`. Si el proceso muere y se vuelve a lanzar, salta automáticamente las réplicas ya completadas (status `optimal` o `feasible`).

## Instalación de solvers libres

```bash
sudo apt install coinor-cbc    # CBC
sudo apt install glpk-utils    # GLPK
pip install highspy             # HiGHS (ya en pyproject.toml)
```

Gurobi requiere licencia académica separada (`grbgetkey`).
