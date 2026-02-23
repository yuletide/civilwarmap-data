# Civil War Cartogram Worklog

## Scope
Track cartogram generation runs, exact inputs/flags, outputs, and quality observations for publication-ready maps.

## Core Inputs
- Geometry source: `us_state_1860_nspop_proj.geojson`
- Geometry (validated): `us_state_1860_nspop_proj_valid.geojson`
- Base data CSV: `output/us_state_1860_modern_data.csv`
- Flipped data CSV (LA/TN/AR toggled): `output/us_state_1860_modern_data_flipped.csv`
- Tool binary: `cartogram-cpp/build/Release/cartogram`

## Run History (2026-02-23)

| Run ID | Intent | Geometry Input | CSV Input | Flags | Primary Outputs | Observations |
|---|---|---|---|---|---|---|
| R1-modern-script | First stable modern run from script | `us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data.csv` | `--skip_projection --disable_simplify_and_densify --plot_polygons --export_preprocessed --verbose` | `output/us_state_1860_modern_data_output.svg`, `output/us_state_1860_modern_data_cartogram.geojson`, `output/us_state_1860_modern_data_cartogram_valid.geojson` | Root fix: input geometry must be pre-validated + projection skipped (input already projected). Output geometry had minor invalids (4) repaired to 0 in `_valid.geojson`. |
| R2-flipped-1863style | Alternate political coloring pass | `us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_flipped.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose` | `output/us_state_1860_modern_data_flipped_output.svg`, `output/us_state_1860_modern_data_flipped_C_cartogram.svg`, `output/us_state_1860_modern_data_flipped_C_cartogram.pdf` | LA/TN/AR color flip produced cleaner comparison variant. Maine visual clutter improved versus no tiny-polygon removal. |
| R3-1861-true-base | True 1861-style (non-flipped) vector run | `us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose` | `output/us_state_1860_modern_data_output.svg`, `output/us_state_1860_modern_data_C_cartogram.svg`, `output/flowcartogram1861.pdf` | Correct non-flipped styling confirmed. |
| R4-1861-print | Higher fidelity print candidate | `us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_1861_print.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --n_points 50000 --min_integrations 20 --max_permitted_area_error 0.003 --quadtree_leaf_count_factor 512 --verbose` | `output/us_state_1860_modern_data_1861_print_output.svg`, `output/us_state_1860_modern_data_1861_print_C_cartogram.svg` | Convergence improved substantially; Kentucky thin spur still visually present. |
| R5-1861-book | Stronger tiny-fragment suppression | `us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_1861_book.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0015 --n_points 50000 --min_integrations 20 --max_permitted_area_error 0.003 --quadtree_leaf_count_factor 512 --verbose` | `output/us_state_1860_modern_data_1861_book_output.svg`, `output/us_state_1860_modern_data_1861_book_C_cartogram.svg` | Cleaner than R4 for coastal/island clutter. |
| R6-1861-iter40 | Publication-focused high-iteration pass | `us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_1861_iter40.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0015 --n_points 50000 --min_integrations 40 --max_permitted_area_error 0.002 --quadtree_leaf_count_factor 512 --verbose` | `output/us_state_1860_modern_data_1861_iter40_output.svg`, `output/us_state_1860_modern_data_1861_iter40_C_cartogram.svg` | Very strong area convergence; Kentucky spur persisted, suggesting geometry/simplification artifact more than insufficient iterations. |

## Current Best Candidates
- 1861 non-flipped, publication candidate: `output/us_state_1860_modern_data_1861_iter40_output.svg`
- 1863-style flipped comparison: `output/us_state_1860_modern_data_flipped_output.svg`

## Open Quality Check
- Kentucky spur artifact likely linked to geometry simplification/topology handling.
- Next A/B run to confirm:
  - Same as R6 **with** `--disable_simplify_and_densify`
  - Compare Kentucky outline in SVG directly.

## Notes
- If map is already projected (as here, ESRI:102003), keep `--skip_projection` to avoid NaN bounding box failures.
- Keep `--plot_polygons` enabled for vector outputs (SVG/PDF), since GeoJSON alone is not print-friendly.
