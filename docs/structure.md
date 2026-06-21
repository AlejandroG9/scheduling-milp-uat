# scheduling-milp-uat — Estructura del proyecto

Repositorio de experimentación que acompaña el artículo:
> *Design of a Schedule Assignment Model for an Educational Program: Implementation with Pyomo*
> Mathematics (MDPI), manuscript ID: mathematics-3738359

## Estructura

```
scheduling-milp-uat/
├─ data/
│  ├─ raw/           # Datos originales — NO versionados (.gitignore)
│  └─ anonymized/    # Datos con nombres reemplazados por IDs — versionados
├─ model/            # Constructor del modelo MILP (Pyomo)
├─ solvers/          # Interfaces por solver: gurobi, cbc, glpk, highs
├─ runners/
│  ├─ benchmark.py       # A1 — comparación de solvers
│  ├─ sensitivity.py     # A3 — sensibilidad de pesos tn/md/ags
│  └─ full_experiment.py # Experimento principal 9×30 réplicas
├─ results/
│  └─ experiments.db     # SQLite con todas las corridas (no versionado)
├─ analysis/         # Scripts para generar tablas LaTeX del artículo
├─ scripts/
│  └─ init_db.py     # Inicializa la base de datos
└─ docs/
   └─ structure.md   # Este archivo
```

## Primeros pasos

```bash
# 1. Instalar dependencias
pip install pyomo pandas openpyxl psutil highspy

# 2. Inicializar base de datos
python scripts/init_db.py

# 3. Colocar datos anonimizados en data/anonymized/

# 4. Correr experimento completo
python runners/full_experiment.py

# 5. Correr benchmark de solvers (requiere CBC, GLPK y HiGHS instalados)
python runners/benchmark.py
```

## Solvers soportados

| Solver  | Tipo       | Instalación              |
|:--------|:-----------|:-------------------------|
| Gurobi  | Comercial  | Requiere licencia        |
| CBC     | Gratuito   | `apt install coinor-cbc` |
| GLPK    | Gratuito   | `apt install glpk-utils` |
| HiGHS   | Gratuito   | `pip install highspy`    |
