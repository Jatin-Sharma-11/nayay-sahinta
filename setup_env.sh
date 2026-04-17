#!/usr/bin/env bash
# ============================================================
#  Nyaya-Sahayak — Conda Environment Setup
#  Creates conda env "dbx", installs all deps, clones PageIndex
# ============================================================
set -e
CONDA_ENV="dbx"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚖️  Nyaya-Sahayak Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Create or reuse conda env
if conda env list | grep -q "^${CONDA_ENV} "; then
    echo "[1/6] Conda env '${CONDA_ENV}' already exists — reusing."
else
    echo "[1/6] Creating conda env '${CONDA_ENV}' with Python 3.10..."
    conda create -y -n "${CONDA_ENV}" python=3.10
fi

# 2. Activate
eval "$(conda shell.bash hook)"
conda activate "${CONDA_ENV}"
echo "[2/6] Activated: $(which python) | $(python --version)"

# 3. Install Java (PySpark dependency) if missing
if ! java -version 2>/dev/null; then
    echo "[3/6] Installing OpenJDK 11 for PySpark..."
    conda install -y -c conda-forge openjdk=11
else
    echo "[3/6] Java already available: $(java -version 2>&1 | head -1)"
fi

# 4. Install pip packages
echo "[4/6] Installing Python packages..."
pip install --upgrade pip --quiet
pip install -r "${PROJECT_DIR}/requirements_dbx.txt" --quiet
echo "      ✅ Python packages installed"

# 5. Clone & install PageIndex
VENDOR_DIR="${PROJECT_DIR}/vendor"
PAGEINDEX_DIR="${VENDOR_DIR}/PageIndex"
mkdir -p "${VENDOR_DIR}"

if [ -d "${PAGEINDEX_DIR}" ]; then
    echo "[5/6] PageIndex already cloned — pulling latest..."
    git -C "${PAGEINDEX_DIR}" pull --quiet
else
    echo "[5/6] Cloning PageIndex from GitHub..."
    git clone --depth=1 https://github.com/VectifyAI/PageIndex.git "${PAGEINDEX_DIR}"
fi
pip install -r "${PAGEINDEX_DIR}/requirements.txt" --quiet
echo "      ✅ PageIndex installed from vendor/"

# 6. Set up .env
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    echo "[6/6] Creating .env from template..."
    cp "${PROJECT_DIR}/.env.template" "${PROJECT_DIR}/.env"
    echo "      ⚠️  Please edit .env to confirm your HF token."
else
    echo "[6/6] .env already exists — skipping."
fi

# 7. Create data dirs
mkdir -p "${PROJECT_DIR}/data/bns_index" "${PROJECT_DIR}/data/ipc_index"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  Setup complete!"
echo ""
echo "Next steps:"
echo "  conda activate ${CONDA_ENV}"
echo "  bash run_nyaya.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
