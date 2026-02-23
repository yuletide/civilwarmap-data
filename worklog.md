# Civil War Cartogram Worklog

## Scope
Track cartogram generation runs, exact inputs/flags, outputs, and quality observations for publication-ready maps.

## Core Inputs
- Geometry source: `data/us_state_1860_nspop_proj.geojson`
- Geometry (validated): `data/us_state_1860_nspop_proj_valid.geojson`
- 1861 data CSV (darker; LA/TN/AR dark): `output/us_state_1861_modern_data.csv`
- 1863 data CSV (whiter; LA/TN/AR white): `output/us_state_1863_modern_data.csv`
- Tool binary: `cartogram-cpp/build/Release/cartogram`

## Run History (2026-02-23)

| Run ID | Intent | Geometry Input | CSV Input | Flags | Primary Outputs | Observations |
|---|---|---|---|---|---|---|
| R1-modern-script | First stable modern run from script | `data/us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data.csv` | `--skip_projection --disable_simplify_and_densify --plot_polygons --export_preprocessed --verbose` | `output/us_state_1860_modern_data_output.svg`, `output/us_state_1860_modern_data_cartogram.geojson`, `output/us_state_1860_modern_data_cartogram_valid.geojson` | Root fix: input geometry must be pre-validated + projection skipped (input already projected). Output geometry had minor invalids (4) repaired to 0 in `_valid.geojson`. |
| R2-flipped-1863style | Alternate political coloring pass | `data/us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_flipped.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose` | `output/us_state_1860_modern_data_flipped_output.svg`, `output/us_state_1860_modern_data_flipped_C_cartogram.svg`, `output/us_state_1860_modern_data_flipped_C_cartogram.pdf` | LA/TN/AR color flip produced cleaner comparison variant. Maine visual clutter improved versus no tiny-polygon removal. |
| R3-1861-true-base | True 1861-style (non-flipped) vector run | `data/us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --verbose` | `output/us_state_1860_modern_data_output.svg`, `output/us_state_1860_modern_data_C_cartogram.svg`, `output/flowcartogram1861.pdf` | Correct non-flipped styling confirmed. |
| R4-1861-print | Higher fidelity print candidate | `data/us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_1861_print.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0005 --n_points 50000 --min_integrations 20 --max_permitted_area_error 0.003 --quadtree_leaf_count_factor 512 --verbose` | `output/us_state_1860_modern_data_1861_print_output.svg`, `output/us_state_1860_modern_data_1861_print_C_cartogram.svg` | Convergence improved substantially; Kentucky thin spur still visually present. |
| R5-1861-book | Stronger tiny-fragment suppression | `data/us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_1861_book.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0015 --n_points 50000 --min_integrations 20 --max_permitted_area_error 0.003 --quadtree_leaf_count_factor 512 --verbose` | `output/us_state_1860_modern_data_1861_book_output.svg`, `output/us_state_1860_modern_data_1861_book_C_cartogram.svg` | Cleaner than R4 for coastal/island clutter. |
| R6-1861-iter40 | Publication-focused high-iteration pass | `data/us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_1861_iter40.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0015 --n_points 50000 --min_integrations 40 --max_permitted_area_error 0.002 --quadtree_leaf_count_factor 512 --verbose` | `output/us_state_1860_modern_data_1861_iter40_output.svg`, `output/us_state_1860_modern_data_1861_iter40_C_cartogram.svg` | Very strong area convergence; Kentucky spur persisted, suggesting geometry/simplification artifact more than insufficient iterations. |
| R7-1861-iter40-nosimp | A/B test with simplification disabled | `data/us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_1861_iter40_nosimp.csv` | `--skip_projection --plot_polygons --disable_simplify_and_densify --remove_tiny_polygons --minimum_polygon_area 0.0015 --min_integrations 40 --max_permitted_area_error 0.002 --quadtree_leaf_count_factor 512 --verbose` | `output/us_state_1860_modern_data_1861_iter40_nosimp_output.svg`, `output/us_state_1860_modern_data_1861_iter40_nosimp_C_cartogram.svg` | Kentucky spike metric improved, but output had topology/rendering failure symptoms (Kentucky and Florida appeared broken/missing in final map). GeoJSON check: 2 invalid + 2 non-simple features. Rejected for publication. |
| R8-1861-balanced-default-quadtree | Balanced publication run with default quadtree | `data/us_state_1860_nspop_proj_valid.geojson` | `output/us_state_1860_modern_data_1861_balanced.csv` | `--skip_projection --plot_polygons --remove_tiny_polygons --minimum_polygon_area 0.0008 --n_points 50000 --min_integrations 40 --max_permitted_area_error 0.002 --verbose` | `output/us_state_1860_modern_data_1861_balanced_output.svg`, `output/us_state_1860_modern_data_1861_balanced_C_cartogram.svg` | No quadtree override. Kentucky and Florida present and valid/simple. Keeps topology safety while reducing catastrophic artifacts from no-simplification run. |

## Current Best Candidates
- 1861 non-flipped, publication candidate (current): `output/us_state_1860_modern_data_1861_balanced_output.svg`
- 1863-style flipped comparison: `output/us_state_1860_modern_data_flipped_output.svg`

## A/B Findings (Kentucky Sliver)
- The sliver is influenced by simplification/deformation, but fully disabling simplification is not acceptable for final output (topology/render failures).
- Overriding quadtree (`--quadtree_leaf_count_factor 512`) did not remove the issue enough to justify complexity.
- Best compromise so far: R8 balanced run (default quadtree, simplification on, high points + high iterations).

## Open Quality Check
- Optional final polish run: keep R8 settings and slightly reduce `--minimum_polygon_area` to `0.0007` or `0.0006` if any state edge still looks clipped in print proof.

## Notes
- If map is already projected (as here, ESRI:102003), keep `--skip_projection` to avoid NaN bounding box failures.
- Keep `--plot_polygons` enabled for vector outputs (SVG/PDF), since GeoJSON alone is not print-friendly.
