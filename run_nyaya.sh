#!/usr/bin/env bash
# ============================================================
#  Nyaya-Sahayak — One-Click Launch Script
#  Activates dbx env, runs pipeline (if needed), starts app
# ============================================================
set -e
CONDA_ENV="dbx"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"

eval "$(conda shell.bash hook)"
conda activate "${CONDA_ENV}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚖️  Nyaya-Sahayak Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run data pipeline only if BNS markdown hasn't been generated yet
if [ ! -f "${PROJECT_DIR}/data/bns_full.md" ]; then
    echo "[1/2] Running data pipeline (PySpark)..."
    python -m nyaya_sahayak.data_pipeline
else
    echo "[1/2] Data pipeline already run — skipping (delete data/ to rerun)."
fi

echo "[2/2] Launching Streamlit app..."
echo ""
echo "  → Open: http://localhost:8501"
echo ""
streamlit run app.py \
    --server.port 8501 \
    --server.headless true \
    --server.fileWatcherType none \
    --browser.gatherUsageStats false \
    --theme.base dark \
    --theme.primaryColor "#f59e0b" \
    --theme.backgroundColor "#050d1a" \
    --theme.secondaryBackgroundColor "#0a1628" \
    --theme.textColor "#e2e8f0"
