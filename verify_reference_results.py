#!/usr/bin/env python3
"""Check that archived SC-TAS outputs match the published rounded values."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "reference_results"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def find_row(data: list[dict[str, str]], column: str, value: str) -> dict[str, str]:
    for row in data:
        if row[column] == value:
            return row
    raise AssertionError(f"Missing row {column}={value!r}")


def close(actual: float, expected: float, tolerance: float = 0.0006) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise AssertionError(f"expected {expected:.4f}, found {actual:.8f}")


def main() -> int:
    main_table = rows(ROOT / "revised_real" / "table1_main_results.csv")
    expected_main = {
        "FreeLook prior": (0.849, 0.298),
        "TAS NR": (0.827, 0.281),
        "TAS FR": (0.782, 0.305),
    }
    for method, (cc, jsd) in expected_main.items():
        row = find_row(main_table, "Method", method)
        close(float(row["CC_mean"]), cc)
        close(float(row["JSD_mean"]), jsd)

    cross = rows(ROOT / "crossdataset_baselines" / "table_g1_crossdataset.csv")
    expected_cross = {
        ("INT", "SC-TAS NR"): (0.670, 0.324),
        ("INT", "Prior only"): (0.695, 0.304),
        ("R1 (stability)", "SC-TAS NR"): (0.957, 0.130),
    }
    for (dataset, method), (cc, jsd) in expected_cross.items():
        row = next(
            row for row in cross
            if row["Dataset"] == dataset and row["Method"] == method)
        close(float(row["CC_mean"]), cc)
        close(float(row["JSD_mean"]), jsd)

    with (ROOT / "unet_lite_baseline" / "unet_lite_summary.json").open(
            encoding="utf-8") as handle:
        unet = json.load(handle)
    assert unet["n_parameters"] == 118129
    close(float(unet["r2_loco"]["cc_mean"]), 0.887)
    close(float(unet["r2_loco"]["jsd_mean"]), 0.373)
    close(float(unet["int_zeroshot"]["cc_mean"]), 0.685)
    close(float(unet["int_zeroshot"]["jsd_mean"]), 0.438)

    stress = rows(ROOT / "ablation_sensitivity" / "stability_stress_summary.csv")
    default = find_row(stress, "beta", "0.3")
    aggressive = find_row(stress, "beta", "2.0")
    close(float(default["activation_rate_pct"]), 0.0)
    close(float(aggressive["activation_rate_pct"]), 98.125)
    close(float(aggressive["delta_cc"]), 0.162)

    print("Archived reference results match the published rounded values.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, StopIteration, FileNotFoundError) as exc:
        print(f"Reference-result verification failed: {exc}", file=sys.stderr)
        sys.exit(1)
