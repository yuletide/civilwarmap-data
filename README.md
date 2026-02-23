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

## Run 1861 map (darker; LA/TN/AR dark)
```bash
REPO_ROOT="$(pwd)"
cd output
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/data/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1861_modern_data.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose
```

## Run 1863 map (whiter; LA/TN/AR white)
```bash
REPO_ROOT="$(pwd)"
cd output
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/data/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1863_modern_data.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose
```

## Run publication-focused iter40 pass
```bash
REPO_ROOT="$(pwd)"
cd output
cp us_state_1861_modern_data.csv us_state_1861_modern_data_iter40.csv
"$REPO_ROOT/cartogram-cpp/build/Release/cartogram" \
  "$REPO_ROOT/data/us_state_1860_nspop_proj_valid.geojson" \
  "$REPO_ROOT/output/us_state_1861_modern_data_iter40.csv" \
  --skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0015 \
  --n_points 50000 --min_integrations 40 --max_permitted_area_error 0.002 --quadtree_leaf_count_factor 512 --verbose
```

## Key outputs
- `output/us_state_1861_modern_data_output.svg`
- `output/us_state_1863_modern_data_output.svg`

For run-by-run notes and observations, see `worklog.md`.

## Data source citation (NHGIS)

Primary tabular inputs come from IPUMS NHGIS (state-level 1860 extracts).

Recommended citation:

```text
IPUMS National Historical Geographic Information System: Version 17.0 [dataset].
Minneapolis, MN: IPUMS. 2022. https://doi.org/10.18128/D050.V17.0
```

## Cartogram method and software citations

Algorithm (2018):

```text
Gastner, M. T., Seguy, V., & More, P. (2018). Fast flow-based algorithm for creating
density-equalizing map projections. Proceedings of the National Academy of Sciences,
115(10), E2156-E2164. https://doi.org/10.1073/pnas.1712674115
```

Software (2022):

```text
Gastner, M. T., adisidev, fillingthemoon, Nguyen Phong, L., nihalzp,
vuminhhieunus2019, sevvalbbayram, & morrcriven. (2022).
mgastner/cartogram-cpp: C++ Cartogram Generator (alpha v0.0.0) (v0.0.0-alpha).
Zenodo. https://doi.org/10.5281/zenodo.6346715
```
