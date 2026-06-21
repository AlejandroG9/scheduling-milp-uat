#!/bin/bash
# Ejecuta la experimentación completa para el artículo.
# Requiere: venv activado y licencia de Gurobi disponible.
# Uso: bash scripts/run_experiments.sh

set -e   # detener si cualquier comando falla

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "======================================================"
echo " Inicializando base de datos"
echo "======================================================"
python scripts/init_db.py

echo ""
echo "======================================================"
echo " E1 — Experimento completo (9 semestres × 10 réplicas)"
echo "======================================================"
python runners/full_experiment.py

echo ""
echo "======================================================"
echo " E2 — Benchmark de solvers (Gurobi / HiGHS / CBC / GLPK)"
echo "======================================================"
python runners/benchmark.py

echo ""
echo "======================================================"
echo " E3 — Análisis de sensibilidad de pesos"
echo "======================================================"
python runners/sensitivity.py

echo ""
echo "======================================================"
echo " Experimentación completa finalizada."
echo " Resultados en: results/experiments.db"
echo "======================================================"
