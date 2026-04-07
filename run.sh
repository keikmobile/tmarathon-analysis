#!/bin/bash
# run.sh — GPX + CSV + splits → race_analysis_YYYY-MM-DD.html を一括生成
#
# 使い方:
#   ./run.sh YYYY-MM-DD
#   ./run.sh YYYY-MM-DD /path/to/route.gpx
#   ./run.sh YYYY-MM-DD /path/to/route.gpx /path/to/workouts.csv
#   ./run.sh YYYY-MM-DD /path/to/route.gpx /path/to/workouts.csv /path/to/splits.json

set -e

DATE=${1:?"使い方: ./run.sh YYYY-MM-DD [gpx_path] [csv_path] [splits_json]"}
GPX=${2:-data/input/route_${DATE}.gpx}
CSV=${3:-data/input/running_workouts.csv}
SPLITS=${4:-data/input/splits_${DATE}.json}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "レース分析 パイプライン: $DATE"
echo "========================================"
echo "GPX  : $GPX"
echo "CSV  : $CSV"
echo "Splits: $SPLITS"
echo ""

PYTHON=${PYTHON:-$(command -v python3 || command -v python)}

# Step 1: GPXパース
echo "[1/3] GPXパース..."
"$PYTHON" scripts/parse_gpx.py "$GPX" data/output/gpx_data.json
echo ""

# Step 2: CSVマージ
echo "[2/3] CSVマージ..."
"$PYTHON" scripts/merge_csv.py data/output/gpx_data.json "$CSV" "$SPLITS" data/output/race_data.json
echo ""

# Step 3: HTML生成
OUT_HTML="data/output/race_analysis_${DATE}.html"
echo "[3/3] HTML生成..."
"$PYTHON" scripts/render_html.py data/output/race_data.json "$OUT_HTML"
echo ""

# docs/ にコピー（GitHub Pages用）
mkdir -p docs
cp "$OUT_HTML" "docs/race_analysis_${DATE}.html"
echo "docs/ にコピー: docs/race_analysis_${DATE}.html"

echo "========================================"
echo "完了: $OUT_HTML"
echo "========================================"
