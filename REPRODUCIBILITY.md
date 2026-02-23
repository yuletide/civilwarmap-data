# Civil War Cartogram Reproducibility

This repository tracks reproducible generation of 1860/1861-style Civil War cartograms with `cartogram-cpp`.

## 1) Build modern cartogram binary

From `cartogram-cpp/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
conan install . --build=missing -s build_type=Release -s compiler.cppstd=20
cmake -B build/Release -S . -DCMAKE_TOOLCHAIN_FILE=build/Release/generators/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release
cmake --build build/Release -j4
```

Binary path used:

```bash
./cartogram-cpp/build/Release/cartogram
```

## 2) Prepare validated geometry + base CSV

From repo root:

```bash
REPO_ROOT="$(pwd)"
"$REPO_ROOT/.venv/bin/python" run_modern_1860.py
```

This creates:
- `us_state_1860_nspop_proj_valid.geojson`
- `output/us_state_1860_modern_data.csv`

## 3) Reproduce key map outputs

### A) True 1861-style (non-flipped)

```bash
REPO_ROOT="$(pwd)"
cd output
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1860_modern_data.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose
```

Primary output:
- `output/us_state_1860_modern_data_output.svg`

### B) Flipped political variant (LA/TN/AR)

```bash
REPO_ROOT="$(pwd)"
"$REPO_ROOT/.venv/bin/python" - <<'PY'
import csv
from pathlib import Path
src = Path('output/us_state_1860_modern_data.csv')
dst = Path('output/us_state_1860_modern_data_flipped.csv')
flip_states = {'Louisiana', 'Tennessee', 'Arkansas'}
rows = list(csv.DictReader(src.open(newline='')))
for r in rows:
    if r['statenam'] in flip_states:
        r['Color'] = '#F1F1F1' if r['Color'].strip().lower() == '#727272' else '#727272'
with dst.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(dst)
PY

cd output
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1860_modern_data_flipped.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose
```

Primary output:
- `output/us_state_1860_modern_data_flipped_output.svg`

### C) Publication-focused iter40 pass

```bash
REPO_ROOT="$(pwd)"
cd output
cp us_state_1860_modern_data.csv us_state_1860_modern_data_1861_iter40.csv
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1860_modern_data_1861_iter40.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0015 \
  --n_points 50000 --min_integrations 40 --max_permitted_area_error 0.002 --quadtree_leaf_count_factor 512 --verbose
```

Primary output:
- `output/us_state_1860_modern_data_1861_iter40_output.svg`

## 4) Quality notes

- Input is already projected (ESRI:102003), so `--skip_projection` is required to avoid NaN bounds failures.
- For print, prefer SVG/PDF outputs from `--plot_polygons` over large GeoJSON artifacts.
- See `worklog.md` for chronological run observations and artifact notes (Maine/Kentucky checks).
