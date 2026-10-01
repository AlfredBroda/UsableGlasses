#!/usr/bin/env python3
"""Build a UsableGlasses Workshop package in the Ostranauts Mods directory."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_FILE = PROJECT_ROOT / "UsableGlasses.csproj"
DEFAULT_SOURCE = PROJECT_ROOT / "bin" / "Release" / "UsableGlasses.dll"
DEFAULT_PROPS = PROJECT_ROOT / "Config.Build.user.props"
DEFAULT_METADATA = PROJECT_ROOT / "mod_info.json"


def read_property(props_path: Path, property_name: str) -> str:
    try:
        root = ET.parse(props_path).getroot()
    except (ET.ParseError, OSError) as error:
        raise RuntimeError(f"Could not read {props_path}: {error}") from error

    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == property_name:
            value = (element.text or "").strip()
            if value:
                return value

    raise RuntimeError(f"{property_name} was not found in {props_path}")


def validate_metadata(metadata_path: Path) -> None:
    try:
        with metadata_path.open(encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read metadata {metadata_path}: {error}") from error

    if not isinstance(metadata, list) or not metadata:
        raise RuntimeError(f"Metadata must be a non-empty JSON array: {metadata_path}")


def build_release() -> None:
    print(f"Building {PROJECT_FILE.name} in Release configuration...")
    try:
        subprocess.run(
            ["dotnet", "build", str(PROJECT_FILE), "--configuration", "Release"],
            cwd=PROJECT_ROOT,
            check=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("dotnet was not found on PATH") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Release build failed with exit code {error.returncode}") from error


def deploy(
    source: Path,
    props_path: Path,
    metadata_path: Path,
    dry_run: bool,
) -> Path:
    if not source.is_file():
        raise RuntimeError(
            f"Release DLL not found: {source}\n"
            "Build it first with: dotnet build --configuration Release"
        )
    if not metadata_path.is_file():
        raise RuntimeError(f"Metadata file not found: {metadata_path}")
    validate_metadata(metadata_path)
    source_images_dir = PROJECT_ROOT / "images"
    if not (source_images_dir / "preview.png").is_file():
        raise RuntimeError(
            f"Preview image not found: {source_images_dir / 'preview.png'}\n"
            "Add images/preview.png to the project."
        )

    bepinex_dir = Path(read_property(props_path, "BepInExDir"))
    if not bepinex_dir.is_dir():
        raise RuntimeError(f"BepInExDir does not exist: {bepinex_dir}")

    game_dir = bepinex_dir.parent.parent
    package_dir = game_dir / "Ostranauts_Data" / "Mods" / "UsableGlasses"
    plugins_dir = package_dir / "plugins"
    source_data_dir = PROJECT_ROOT / "data"
    destination = plugins_dir / source.name

    if dry_run:
        print(f"Would create package: {package_dir}")
        print(f"Would copy {metadata_path.name} -> {package_dir / 'mod_info.json'}")
        print(f"Would copy {source.name} -> {destination}")
        print(f"Would copy {source_data_dir} -> {package_dir / 'data'}")
        print(f"Would copy {source_images_dir} -> {package_dir / 'images'}")
        print(
            f"Would move {package_dir / 'images' / 'preview.png'} -> "
            f"{package_dir / 'preview.png'}"
        )
        return package_dir

    if package_dir.exists():
        print(f"Removing existing package directory: {package_dir}")
        shutil.rmtree(package_dir)

    plugins_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(metadata_path, package_dir / "mod_info.json")
    shutil.copy2(source, destination)
    shutil.copytree(source_data_dir, package_dir / "data", dirs_exist_ok=True)
    images_dir = package_dir / "images"
    shutil.copytree(source_images_dir, images_dir, dirs_exist_ok=True)
    shutil.move(str(images_dir / "preview.png"), str(package_dir / "preview.png"))
    print(f"Created Workshop package at {package_dir}")
    return package_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Release DLL to deploy (default: bin/Release/net48/UsableGlasses.dll)",
    )
    parser.add_argument(
        "--props",
        type=Path,
        default=DEFAULT_PROPS,
        help="MSBuild props file containing BepInExDir (default: Config.Build.user.props)",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA,
        help="Metadata source copied as mod_info.json (default: mod_info.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the deployment path without copying the DLL",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip the Release build and package the existing DLL",
    )
    arguments = parser.parse_args()

    try:
        if not arguments.no_build:
            build_release()
        deploy(
            arguments.source.resolve(),
            arguments.props.resolve(),
            arguments.metadata.resolve(),
            arguments.dry_run,
        )
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
