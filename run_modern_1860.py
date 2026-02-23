import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.validation import make_valid


BASE = Path(__file__).resolve().parent
OUTPUT_DIR = BASE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR = BASE / "data"

SOURCE_GEOJSON = DATA_DIR / "us_state_1860_nspop_proj.geojson"
VALID_INPUT_GEOJSON = DATA_DIR / "us_state_1860_nspop_proj_valid.geojson"
CSV_1863 = OUTPUT_DIR / "us_state_1863_modern_data.csv"
CSV_1861 = OUTPUT_DIR / "us_state_1861_modern_data.csv"
CARTOGRAM_BIN = BASE / "cartogram-cpp" / "build" / "Release" / "cartogram"


def count_invalid_features(geojson: dict) -> int:
    invalid_count = 0
    for feature in geojson["features"]:
        geom = shape(feature["geometry"])
        if not geom.is_valid or not geom.is_simple:
            invalid_count += 1
    return invalid_count


def make_valid_geojson(src: Path, dst: Path) -> None:
    with src.open() as f:
        geojson = json.load(f)

    for feature in geojson["features"]:
        geom = shape(feature["geometry"])
        if not geom.is_valid or not geom.is_simple:
            feature["geometry"] = mapping(make_valid(geom))

    with dst.open("w") as f:
        json.dump(geojson, f)


def build_year_csv(
    input_geojson: Path,
    out_csv: Path,
    confederate_overrides: dict[str, int] | None = None,
) -> int:
    overrides = confederate_overrides or {}

    with input_geojson.open() as f:
        geojson = json.load(f)

    rows = []
    for feature in geojson["features"]:
        props = feature.get("properties", {})
        state_name = props.get("statenam")
        population = props.get("pop1860nonslave_adj")
        confederate = int(props.get("confederate", 0))
        if state_name in overrides:
            confederate = int(overrides[state_name])

        if not state_name or population in (None, ""):
            continue

        color = "#727272" if confederate == 1 else "#F1F1F1"
        rows.append((state_name, population, color))

    rows.sort(key=lambda item: item[0])

    with out_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["statenam", "Population", "Color"])
        writer.writerows(rows)

    return len(rows)


def run_modern_cartogram(input_geojson: Path, input_csv: Path) -> subprocess.CompletedProcess:
    cmd = [
        str(CARTOGRAM_BIN),
        str(input_geojson),
        str(input_csv),
        "--skip_projection",
        "--plot_polygons",
        "--verbose",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(OUTPUT_DIR))


def write_output_log(path: Path, content: str) -> None:
    with path.open("w") as f:
        f.write(content)


def fix_output_geometry(output_geojson: Path) -> Path:
    fixed_output = output_geojson.with_name(output_geojson.stem + "_valid.geojson")
    make_valid_geojson(output_geojson, fixed_output)
    return fixed_output


def fix_svg_fill_rule(svg_path: Path) -> None:
    """Replace evenodd fill rule with nonzero to avoid holes from self-crossing paths."""
    text = svg_path.read_text()
    text = text.replace('fill-rule="evenodd"', 'fill-rule="nonzero"')
    svg_path.write_text(text)


def _stamp_artifacts(stem: str, timestamp: str) -> list[Path]:
    """Rename cartogram output files from `{stem}_*` to `{stem}_{timestamp}_*`."""
    suffixes = [
        "_output.svg",
    ]
    stamped: list[Path] = []
    for suffix in suffixes:
        src = OUTPUT_DIR / f"{stem}{suffix}"
        if src.exists():
            dst = OUTPUT_DIR / f"{stem}_{timestamp}{suffix}"
            src.rename(dst)
            stamped.append(dst)
    return stamped


def run_year_cartogram(year_label: str, csv_path: Path, timestamp: str) -> int:
    result = run_modern_cartogram(VALID_INPUT_GEOJSON, csv_path)
    write_output_log(OUTPUT_DIR / f"modern_run_{year_label}_{timestamp}.stderr.log", result.stderr)
    write_output_log(OUTPUT_DIR / f"modern_run_{year_label}_{timestamp}.stdout.log", result.stdout)

    if result.returncode != 0:
        print(f"{year_label}: cartogram failed with exit code {result.returncode}.")
        print(f"See output/modern_run_{year_label}_{timestamp}.stderr.log")
        return result.returncode

    cartogram_output = OUTPUT_DIR / f"{csv_path.stem}_cartogram.geojson"
    if not cartogram_output.exists():
        print(f"{year_label}: expected output not found: {cartogram_output}")
        return 3

    with cartogram_output.open() as f:
        output_geojson = json.load(f)

    invalid_before = count_invalid_features(output_geojson)
    fixed_output = fix_output_geometry(cartogram_output)

    with fixed_output.open() as f:
        fixed_geojson = json.load(f)
    invalid_after = count_invalid_features(fixed_geojson)

    # Fix SVG fill rule and stamp output
    output_svg = OUTPUT_DIR / f"{csv_path.stem}_output.svg"
    if output_svg.exists():
        fix_svg_fill_rule(output_svg)

    # Remove debug SVGs (C_cartogram, C_input, input)
    for suffix in ("_C_cartogram.svg", "_C_input.svg", "_input.svg"):
        debug_svg = OUTPUT_DIR / f"{csv_path.stem}{suffix}"
        if debug_svg.exists():
            debug_svg.unlink()

    # Stamp output SVG with timestamp
    stamped = _stamp_artifacts(csv_path.stem, timestamp)

    print(f"{year_label}: stamped {len(stamped)} SVGs with {timestamp}")
    print(f"{year_label}: invalid geometries before/after: {invalid_before}/{invalid_after}")
    print(f"{year_label}: {cartogram_output.name}")
    print(f"{year_label}: {fixed_output.name}")
    for p in stamped:
        print(f"  {p.name}")
    return 0


def main() -> int:
    if not CARTOGRAM_BIN.exists():
        print(f"Missing cartogram binary: {CARTOGRAM_BIN}")
        print("Build modern binary first in cartogram-cpp/build/Release.")
        return 2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Run timestamp: {ts}")

    make_valid_geojson(SOURCE_GEOJSON, VALID_INPUT_GEOJSON)
    csv_rows_1861 = build_year_csv(
        VALID_INPUT_GEOJSON,
        CSV_1861,
        confederate_overrides={
            "Louisiana": 1,
            "Tennessee": 1,
            "Arkansas": 1,
        },
    )
    csv_rows_1863 = build_year_csv(VALID_INPUT_GEOJSON, CSV_1863)

    run_1861 = run_year_cartogram("1861", CSV_1861, ts)
    if run_1861 != 0:
        return run_1861

    run_1863 = run_year_cartogram("1863", CSV_1863, ts)
    if run_1863 != 0:
        return run_1863

    print(f"\nModern runs completed ({ts}).")
    print(f"CSV rows (1861): {csv_rows_1861}  CSV rows (1863): {csv_rows_1863}")
    print(f"CSV (1861): {CSV_1861.name}  CSV (1863): {CSV_1863.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())