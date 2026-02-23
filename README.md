# civilwarmap-data

Build-and-run guide for reproducible Civil War cartogram outputs.

## Prerequisites
- macOS/Linux
- Python 3.10+
- Conan 2.x
- CMake
- A C++20 compiler

## Build cartogram binary
```bash
cd cartogram-cpp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
conan install . --build=missing -s build_type=Release -s compiler.cppstd=20
cmake -B build/Release -S . -DCMAKE_TOOLCHAIN_FILE=build/Release/generators/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release
cmake --build build/Release -j4
```

Binary used by this project:
```bash
./cartogram-cpp/build/Release/cartogram
```

## Generate validated geometry + base CSV
```bash
REPO_ROOT="$(pwd)"
"$REPO_ROOT/.venv/bin/python" run_modern_1860.py
```

## Run 1861 base (non-flipped)
```bash
REPO_ROOT="$(pwd)"
cd output
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/data/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1860_modern_data.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose
```

## Run 1863-style flipped variant
```bash
REPO_ROOT="$(pwd)"
cd output
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/data/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1860_modern_data_flipped.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose
```

## Run publication-focused iter40 pass
```bash
REPO_ROOT="$(pwd)"
cd output
cp us_state_1860_modern_data.csv us_state_1860_modern_data_1861_iter40.csv
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/data/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1860_modern_data_1861_iter40.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0015 \
  --n_points 50000 --min_integrations 40 --max_permitted_area_error 0.002 --quadtree_leaf_count_factor 512 --verbose
```

## Key outputs
- `output/us_state_1860_modern_data_output.svg`
- `output/us_state_1860_modern_data_flipped_output.svg`
- `output/us_state_1860_modern_data_1861_iter40_output.svg`

For run-by-run notes and observations, see `worklog.md`.
