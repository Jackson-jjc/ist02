#!/usr/bin/env python3
"""Validate the public SC-TAS environment and dataset layout."""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PROJECT_ROOT.parent

DEPENDENCIES = {
    "numpy": "numpy",
    "scipy": "scipy",
    "pandas": "pandas",
    "OpenCV": "cv2",
    "Pillow": "PIL",
    "matplotlib": "matplotlib",
    "scikit-learn": "sklearn",
}


def configured_path(variable: str, default: Path) -> Path:
    value = os.environ.get(variable)
    return (Path(value).expanduser() if value else default).resolve()


def check_dependencies(include_torch: bool) -> list[str]:
    missing = []
    packages = dict(DEPENDENCIES)
    if include_torch:
        packages["PyTorch"] = "torch"
    for display_name, module_name in packages.items():
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "version unavailable")
            print(f"[OK] dependency: {display_name} {version}")
        except Exception as exc:  # import errors can include missing binary DLLs
            missing.append(f"{display_name}: {exc}")
            print(f"[FAIL] dependency: {display_name} ({exc})")
    return missing


def files_with_suffix(directory: Path, suffix: str) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == suffix)


def validate_r2(root: Path) -> list[str]:
    errors = []
    required = {
        "OriginalContent": root / "OriginalContent",
        "TestImages": root / "TestImages",
        "SaliencyFreeLook": root / "SaliencyFreeLook",
        "SaliencyScoring": root / "SaliencyScoring",
    }
    for name, directory in required.items():
        if not directory.is_dir():
            errors.append(f"R2 directory missing: {directory}")

    if errors:
        return errors

    pattern = re.compile(r"(.+)_jpgq_\((\d+)\)\.jpg$", re.IGNORECASE)
    stimuli = files_with_suffix(required["TestImages"], ".jpg")
    parsed = [pattern.fullmatch(p.name) for p in stimuli]
    malformed = [p.name for p, match in zip(stimuli, parsed) if match is None]
    if malformed:
        errors.append(f"R2 has {len(malformed)} unrecognised TestImages filenames")

    contents = {match.group(1) for match in parsed if match is not None}
    originals = {
        p.stem.lower()
        for p in required["OriginalContent"].iterdir()
        if p.is_file() and p.suffix.lower() in {".bmp", ".jpg", ".png"}
    }
    missing_originals = sorted(name for name in contents if name.lower() not in originals)
    if missing_originals:
        errors.append(f"R2 originals missing for {len(missing_originals)} contents")

    for saliency_name in ("SaliencyFreeLook", "SaliencyScoring"):
        saliency_names = {p.name.lower() for p in required[saliency_name].iterdir() if p.is_file()}
        missing = [
            p.name for p in stimuli
            if p.name.lower().replace(".jpg", "_combined.jpg") not in saliency_names
        ]
        if missing:
            errors.append(f"R2 {saliency_name} missing {len(missing)} maps")

    if len(contents) != 40 or len(stimuli) != 160:
        errors.append(
            f"R2 expected 40 contents/160 stimuli, found {len(contents)}/{len(stimuli)}")
    return errors


def validate_r1(root: Path) -> list[str]:
    test_dir = root / "TestImages"
    saliency_dir = root / "SaliencyMaps"
    errors = []
    if not test_dir.is_dir():
        errors.append(f"R1 directory missing: {test_dir}")
    if not saliency_dir.is_dir():
        errors.append(f"R1 directory missing: {saliency_dir}")
    if errors:
        return errors
    images = files_with_suffix(test_dir, ".bmp")
    saliency = {p.name.lower() for p in files_with_suffix(saliency_dir, ".bmp")}
    missing = [p.name for p in images if p.name.lower() not in saliency]
    if missing:
        errors.append(f"R1 SaliencyMaps missing {len(missing)} matching maps")
    if len(images) != 29:
        errors.append(f"R1 expected 29 images, found {len(images)}")
    return errors


def validate_int(root: Path) -> list[str]:
    image_dir = root / "images"
    original_dir = image_dir / "originals"
    saliency_dir = root / "Saliency Maps"
    errors = []
    for directory in (image_dir, original_dir, saliency_dir):
        if not directory.is_dir():
            errors.append(f"INT directory missing: {directory}")
    if errors:
        return errors

    pattern = re.compile(r"(.+?)_(blur|jpeg|noise)_\((\d+)\)\.bmp$", re.IGNORECASE)
    stimuli = [p for p in files_with_suffix(image_dir, ".bmp") if pattern.fullmatch(p.name)]
    saliency = {p.name.lower() for p in files_with_suffix(saliency_dir, ".bmp")}
    missing = [
        p.name for p in stimuli
        if f"{p.stem}_AVG.bmp".lower() not in saliency
    ]
    if missing:
        errors.append(f"INT Saliency Maps missing {len(missing)} matching maps")
    originals = files_with_suffix(original_dir, ".bmp")
    if len(stimuli) != 54 or len(originals) != 6:
        errors.append(
            f"INT expected 54 stimuli/6 originals, found {len(stimuli)}/{len(originals)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--datasets", choices=("none", "r2", "all"), default="all",
        help="dataset layouts to validate (default: all)")
    parser.add_argument(
        "--include-unet", action="store_true",
        help="also require PyTorch for the U-Net-lite baseline")
    args = parser.parse_args()

    print(f"[INFO] Python {platform.python_version()} ({platform.platform()})")
    failures = check_dependencies(args.include_unet)
    if args.datasets != "none":
        r2_root = configured_path(
            "SCTAS_R2_ROOT", REPOSITORY_ROOT / "TUD_Task_EyeTracking")
        checks = [("R2", r2_root, validate_r2)]
        if args.datasets == "all":
            checks.extend([
                ("R1", configured_path(
                    "SCTAS_R1_ROOT",
                    REPOSITORY_ROOT / "TUD_LIVE_EyeTracking" / "TUD_LIVE_EyeTracking"),
                 validate_r1),
                ("INT", configured_path(
                    "SCTAS_INT_ROOT", REPOSITORY_ROOT / "TUD_Interactions"),
                 validate_int),
            ])
        for name, root, validator in checks:
            dataset_errors = validator(root)
            if dataset_errors:
                failures.extend(dataset_errors)
                for error in dataset_errors:
                    print(f"[FAIL] {error}")
            else:
                print(f"[OK] {name} dataset: {root}")

    if failures:
        print(f"\nValidation failed with {len(failures)} issue(s).")
        return 1
    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
