# scheduling-milp-uat

Experimental code and data for the article:

> **Design of a Schedule Assignment Model for an Educational Program: Implementation with Pyomo**  
> *Mathematics* (MDPI) — Manuscript ID: mathematics-3738359

This repository contains the MILP formulation, anonymized institutional data, and reproducible experiment scripts used to generate all results reported in the paper.

---

## Contents

```
scheduling-milp-uat/
├─ data/
│  └─ anonymized/        # Institutional dataset (professor names replaced with IDs)
│     └─ modelo_base.db  # SQLite database with all input data
├─ model/
│  ├─ builder.py         # MILP model constructor (Pyomo)
│  ├─ utils.py           # Metrics, timing, and result logging
│  └─ update_data.py     # Updates resource availability between semesters
├─ solvers/
│  ├─ gurobi.py          # Gurobi interface (commercial, requires license)
│  ├─ cbc.py             # CBC interface (free)
│  ├─ glpk.py            # GLPK interface (free)
│  └─ highs.py           # HiGHS interface (free)
├─ runners/
│  ├─ full_experiment.py # Main experiment: 9 semesters × 30 replications
│  ├─ benchmark.py       # Solver comparison (Gurobi vs CBC vs GLPK vs HiGHS)
│  └─ sensitivity.py     # Sensitivity analysis of preference weights (tn, md, ags)
├─ analysis/             # Scripts to generate LaTeX tables for the article
├─ results/              # Generated at runtime — not versioned
├─ scripts/
│  └─ init_db.py         # Initializes the results database
└─ docs/
   └─ structure.md       # Detailed project documentation
```

---

## Model overview

The model is a **Mixed-Integer Linear Program (MILP)** that generates weekly course schedules for the Faculty of Engineering at *Universidad Autónoma de Tamaulipas* (UAT), Mexico.

**Objective:** minimize idle periods between consecutive classes per student group, subject to hard constraints (conflict-free room and instructor assignment) and soft constraints (shift preferences, classroom suitability, and day preferences).

**Key features:**
- Morning and afternoon student shifts
- Parallel groups sharing the same curriculum
- Laboratory and drawing-room assignment rules
- Per-semester decomposition strategy (9 semesters solved independently)

---

## Getting started

### 1. Install dependencies

```bash
pip install pyomo pandas openpyxl psutil highspy
```

For free solvers:
```bash
# CBC
sudo apt install coinor-cbc

# GLPK
sudo apt install glpk-utils
```

### 2. Initialize the results database

```bash
python scripts/init_db.py
```

### 3. Run experiments

```bash
# Main experiment — 9 semesters × 30 replications (requires Gurobi license)
python runners/full_experiment.py

# Solver benchmark — Gurobi vs CBC vs GLPK vs HiGHS
python runners/benchmark.py

# Sensitivity analysis — varies preference weights tn, md, ags
python runners/sensitivity.py
```

---

## Solvers

| Solver | Type       | Pyomo key      | Install                   |
|:-------|:-----------|:---------------|:--------------------------|
| Gurobi | Commercial | `gurobi`       | Academic license required |
| CBC    | Free       | `cbc`          | `apt install coinor-cbc`  |
| GLPK   | Free       | `glpk`         | `apt install glpk-utils`  |
| HiGHS  | Free       | `appsi_highs`  | `pip install highspy`     |

---

## Data

The dataset in `data/anonymized/modelo_base.db` contains the full institutional input used in the article. Professor names have been replaced with anonymous IDs (`Profesor_001`, `Profesor_002`, ...) to comply with privacy requirements. All other data (courses, classrooms, groups, availability, preferences) is unmodified.

---

## Citation

> *Manuscript under review — citation will be added upon publication.*

---

## License

MIT
