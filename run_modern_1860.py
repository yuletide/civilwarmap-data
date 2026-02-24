import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from shapely.geometry import mapping, shape, MultiPolygon
from shapely.validation import make_valid

# Filter sub-polygons smaller than this (m², source projection).
# 100 km² keeps real islands, drops thousands of coastal specks.
DEFAULT_MIN_POLYGON_AREA_M2 = 1e8


BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE / "output"
DATA_DIR = BASE / "data"

DEFAULT_SOURCE_GEOJSON = DATA_DIR / "us_state_1860_nspop_proj.geojson"
CARTOGRAM_BIN = BASE / "cartogram-cpp" / "build" / "Release" / "cartogram"


def count_invalid_features(geojson: dict) -> int:
    invalid_count = 0
    for feature in geojson["features"]:
        geom = shape(feature["geometry"])
        if not geom.is_valid or not geom.is_simple:
            invalid_count += 1
    return invalid_count


def make_valid_geojson(
    src: Path,
    dst: Path,
    *,
    min_polygon_area: float = DEFAULT_MIN_POLYGON_AREA_M2,
    skip_validation: bool = False,
) -> None:
    with src.open() as f:
        geojson = json.load(f)

    total_dropped = 0
    for feature in geojson["features"]:
        geom = shape(feature["geometry"])

        # Fix invalid geometry (unless caller says input is already clean)
        if not skip_validation and (not geom.is_valid or not geom.is_simple):
            geom = make_valid(geom)

        # Drop tiny sub-polygons (coastal specks, slivers)
        if isinstance(geom, MultiPolygon):
            kept = [p for p in geom.geoms if p.area >= min_polygon_area]
            dropped = len(geom.geoms) - len(kept)
            total_dropped += dropped
            if kept:
                geom = MultiPolygon(kept) if len(kept) > 1 else kept[0]
            # else: keep original (don't delete entire states)

        feature["geometry"] = mapping(geom)

    with dst.open("w") as f:
        json.dump(geojson, f)

    print(f"Cleaned geometry: dropped {total_dropped} tiny sub-polygons (threshold {min_polygon_area:.0e} m²)")


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


def run_modern_cartogram(
    input_geojson: Path,
    input_csv: Path,
    *,
    output_dir: Path,
    target_points: int | None = None,
) -> subprocess.CompletedProcess:
    cmd = [
        str(CARTOGRAM_BIN),
        str(input_geojson),
        str(input_csv),
        "--skip_projection",
        "--plot_polygons",
        "--verbose",
    ]
    if target_points is not None:
        cmd.extend(["--n_points", str(target_points)])
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(output_dir))


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


def _stamp_artifacts(stem: str, timestamp: str, *, output_dir: Path) -> list[Path]:
    """Rename cartogram output files from `{stem}_*` to `{stem}_{timestamp}_*`."""
    suffixes = [
        "_output.svg",
    ]
    stamped: list[Path] = []
    for suffix in suffixes:
        src = output_dir / f"{stem}{suffix}"
        if src.exists():
            dst = output_dir / f"{stem}_{timestamp}{suffix}"
            src.rename(dst)
            stamped.append(dst)
    return stamped


def run_year_cartogram(
    year_label: str,
    csv_path: Path,
    timestamp: str,
    *,
    valid_input_geojson: Path,
    output_dir: Path,
    target_points: int | None = None,
) -> int:
    result = run_modern_cartogram(
        valid_input_geojson, csv_path,
        output_dir=output_dir,
        target_points=target_points,
    )
    write_output_log(output_dir / f"modern_run_{year_label}_{timestamp}.stderr.log", result.stderr)
    write_output_log(output_dir / f"modern_run_{year_label}_{timestamp}.stdout.log", result.stdout)

    if result.returncode != 0:
        print(f"{year_label}: cartogram failed with exit code {result.returncode}.")
        print(f"See output/modern_run_{year_label}_{timestamp}.stderr.log")
        return result.returncode

    cartogram_output = output_dir / f"{csv_path.stem}_cartogram.geojson"
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
    output_svg = output_dir / f"{csv_path.stem}_output.svg"
    if output_svg.exists():
        fix_svg_fill_rule(output_svg)

    # Remove debug SVGs (C_cartogram, C_input, input)
    for suffix in ("_C_cartogram.svg", "_C_input.svg", "_input.svg"):
        debug_svg = output_dir / f"{csv_path.stem}{suffix}"
        if debug_svg.exists():
            debug_svg.unlink()

    # Stamp output SVG with timestamp
    stamped = _stamp_artifacts(csv_path.stem, timestamp, output_dir=output_dir)

    print(f"{year_label}: stamped {len(stamped)} SVGs with {timestamp}")
    print(f"{year_label}: invalid geometries before/after: {invalid_before}/{invalid_after}")
    print(f"{year_label}: {cartogram_output.name}")
    print(f"{year_label}: {fixed_output.name}")
    for p in stamped:
        print(f"  {p.name}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run 1860 population cartogram(s) for the Civil War map project.",
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=DEFAULT_SOURCE_GEOJSON,
        help=f"Input GeoJSON file (default: {DEFAULT_SOURCE_GEOJSON.relative_to(BASE)})",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR.relative_to(BASE)})",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=DEFAULT_MIN_POLYGON_AREA_M2,
        help=f"Minimum sub-polygon area in m² to keep (default: {DEFAULT_MIN_POLYGON_AREA_M2:.0e})",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        default=False,
        help="Skip make_valid geometry repair (use when input is already clean/simplified)",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        choices=["1861", "1863"],
        default=["1861", "1863"],
        help="Which year(s) to run (default: both 1861 1863)",
    )
    parser.add_argument(
        "--no-discard",
        action="store_true",
        default=False,
        help="Skip discarding small sub-polygons entirely",
    )
    parser.add_argument(
        "-P", "--target-points",
        type=int,
        default=None,
        help="Target number of points for cartogram-cpp simplify/densify (default: cartogram's own default of 10000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    output_dir: Path = args.output_dir.resolve()
    output_dir.mkdir(exist_ok=True)

    source_geojson: Path = args.input.resolve()
    if not source_geojson.exists():
        print(f"Input file not found: {source_geojson}")
        return 1

    # Derive valid-input path next to input file
    valid_input_geojson = source_geojson.with_name(
        source_geojson.stem + "_valid.geojson"
    )

    csv_1861 = output_dir / "us_state_1861_modern_data.csv"
    csv_1863 = output_dir / "us_state_1863_modern_data.csv"

    if not CARTOGRAM_BIN.exists():
        print(f"Missing cartogram binary: {CARTOGRAM_BIN}")
        print("Build modern binary first in cartogram-cpp/build/Release.")
        return 2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Run timestamp: {ts}")
    print(f"Input:          {source_geojson}")
    print(f"Output dir:     {output_dir}")
    print(f"Min area:       {args.min_area:.0e} m²")
    print(f"Skip validation:{args.skip_validation}")
    print(f"Discard small:  {not args.no_discard}")
    print(f"Target points:  {args.target_points or '10000 (default)'}")
    print(f"Years:          {', '.join(args.years)}")
    print()

    min_area = 0.0 if args.no_discard else args.min_area
    make_valid_geojson(
        source_geojson,
        valid_input_geojson,
        min_polygon_area=min_area,
        skip_validation=args.skip_validation,
    )

    year_configs: dict[str, tuple[Path, dict[str, int] | None]] = {
        "1861": (
            csv_1861,
            {"Louisiana": 1, "Tennessee": 1, "Arkansas": 1},
        ),
        "1863": (csv_1863, None),
    }

    csv_counts: dict[str, int] = {}
    for year in args.years:
        csv_path, overrides = year_configs[year]
        csv_counts[year] = build_year_csv(
            valid_input_geojson, csv_path, confederate_overrides=overrides
        )

    for year in args.years:
        csv_path, _ = year_configs[year]
        rc = run_year_cartogram(
            year,
            csv_path,
            ts,
            valid_input_geojson=valid_input_geojson,
            output_dir=output_dir,
            target_points=args.target_points,
        )
        if rc != 0:
            return rc

    print(f"\nModern runs completed ({ts}).")
    for year in args.years:
        csv_path, _ = year_configs[year]
        print(f"  {year}: {csv_counts[year]} rows -> {csv_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())