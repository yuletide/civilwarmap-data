import csv
import json
import subprocess
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.validation import make_valid


BASE = Path(__file__).resolve().parent
OUTPUT_DIR = BASE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR = BASE / "data"

SOURCE_GEOJSON = DATA_DIR / "us_state_1860_nspop_proj.geojson"
VALID_INPUT_GEOJSON = DATA_DIR / "us_state_1860_nspop_proj_valid.geojson"
MODERN_CSV = OUTPUT_DIR / "us_state_1860_modern_data.csv"
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


def build_modern_csv(input_geojson: Path, out_csv: Path) -> int:
    with input_geojson.open() as f:
        geojson = json.load(f)

    rows = []
    for feature in geojson["features"]:
        props = feature.get("properties", {})
        state_name = props.get("statenam")
        population = props.get("pop1860nonslave_adj")
        confederate = props.get("confederate", 0)

        if not state_name or population in (None, ""):
            continue

        color = "#727272" if int(confederate) == 1 else "#F1F1F1"
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
    return subprocess.run(cmd, capture_output=True, text=True)


def write_output_log(path: Path, content: str) -> None:
    with path.open("w") as f:
        f.write(content)


def fix_output_geometry(output_geojson: Path) -> Path:
    fixed_output = output_geojson.with_name(output_geojson.stem + "_valid.geojson")
    make_valid_geojson(output_geojson, fixed_output)
    return fixed_output


def main() -> int:
    if not CARTOGRAM_BIN.exists():
        print(f"Missing cartogram binary: {CARTOGRAM_BIN}")
        print("Build modern binary first in cartogram-cpp/build/Release.")
        return 2

    make_valid_geojson(SOURCE_GEOJSON, VALID_INPUT_GEOJSON)
    csv_rows = build_modern_csv(VALID_INPUT_GEOJSON, MODERN_CSV)

    result = run_modern_cartogram(VALID_INPUT_GEOJSON, MODERN_CSV)
    write_output_log(OUTPUT_DIR / "modern_run.stderr.log", result.stderr)
    write_output_log(OUTPUT_DIR / "modern_run.stdout.log", result.stdout)

    if result.returncode != 0:
        print(f"Cartogram failed with exit code {result.returncode}.")
        print("See output/modern_run.stderr.log")
        return result.returncode

    cartogram_output = OUTPUT_DIR / "us_state_1860_modern_data_cartogram.geojson"
    if not cartogram_output.exists():
        print(f"Expected output not found: {cartogram_output}")
        return 3

    with cartogram_output.open() as f:
        output_geojson = json.load(f)

    invalid_before = count_invalid_features(output_geojson)
    fixed_output = fix_output_geometry(cartogram_output)

    with fixed_output.open() as f:
        fixed_geojson = json.load(f)
    invalid_after = count_invalid_features(fixed_geojson)
    vector_outputs = sorted(OUTPUT_DIR.glob("us_state_1860_modern_data*.svg"))

    print("Modern run completed.")
    print(f"CSV rows: {csv_rows}")
    print("Vector outputs:")
    for vector_path in vector_outputs:
        print(f"  - {vector_path}")
    print(f"Output: {cartogram_output}")
    print(f"Fixed output: {fixed_output}")
    print(f"Invalid geometries before/after: {invalid_before}/{invalid_after}")
    print("Logs: output/modern_run.stderr.log, output/modern_run.stdout.log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())