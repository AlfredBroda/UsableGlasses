import json
import glob
import re
import subprocess
import sys
import os

from typing import Dict, Set, Union
from pathlib import Path

def git_version():
    """Fetches git tag or falls back to short commit SHA."""
    try:
        tag = run_command(
            "git describe --tags 2>/dev/null", "Git check failed"
        )
        if tag:
            return tag
    except SystemExit:
        pass

    sha = run_command("git rev-parse --short HEAD", "Could not get git commit SHA")
    return f"dev-{sha}"

def run_command(command, error_msg):
    """Helper to safely run shell commands."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {error_msg}")
        print(result.stderr)
        sys.exit(1)
    result.stdout.strip()

def read_version(file_path, field) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        # Ensure the root is a list of items
        if not isinstance(data, list):
            print("Error: Expected a JSON array/list at the root.")
            return "dev"
        
        if len(data) == 1 and field in data[0]:
            return data[0][field]
        else:
            print(F"Error: Expected {field} not found.")

    return "dev"


def safely_write_json(output, entries, preserve_old):
    # Handle reading and appending to the existing overlays JSON file safely
    existing_data = []
    output_path = Path(output)

    if preserve_old:
        print(f"Reading from: {output}")
        if output_path.exists() and output_path.stat().st_size > 0:
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    existing_data = load_json_with_comments(f)
                    # Ensure the existing data is a list
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except json.JSONDecodeError:
                print(
                    f"Warning: {output} was corrupted or not valid JSON. Starting fresh."
                )
                existing_data = []

    combined_data = list(existing_data) + list(entries)
    deduped_data = []
    seen_names = set()

    for item in combined_data:
        if isinstance(item, dict) and "strName" in item:
            key = item["strName"]
            if key in seen_names:
                continue
            seen_names.add(key)
        deduped_data.append(item)

    # Write back to the file with clean formatting
    print(f"Preparing to write into: {output}")
    if not output_path.exists():
        print(f"No files found matching: {output_path}, creating.")
        output_path.touch()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deduped_data, f, indent=2)

    print(
        f"Successfully added {len(entries)} items to '{output_path.resolve()}'"
    )

def load_json_files(file_pattern: str, key_field: str) -> Set[str]:
    """
    Loads all JSON files matching the pattern and extracts the unique values
    of the specified key_field to act as a validation lookup.
    """
    valid_keys = set()
    files = glob.glob(file_pattern)
    
    if not files:
        print(f"Warning: No files found matching pattern: {file_pattern}")
        return valid_keys

    for file_path in files:
        # print(f"Loading: {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = load_json_with_comments(f)
                
                # Handle both a single JSON object or a list of objects per file
                if isinstance(data, dict):
                    items = [data]
                elif isinstance(data, list):
                    items = data
                else:
                    continue
                
                for item in items:
                    if isinstance(item, dict) and key_field in item:
                        valid_keys.add(item[key_field])
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading file {file_path}: {e}")
            return set()
            
    return valid_keys

def filter_list_formatted(names_list, pattern) -> list[str]:
    return [("{"+name).replace(",","},") for name in names_list.splitlines() if pattern in name]

def get_base_pattern(text: str) -> str:
    """
    Strips a suffix like 'SmallA', 'LargeB', etc., from the end of a string.
    Returns the base string.
    """
    # Pattern: Capitalized word + single Capital letter at the end
    pattern = r'[A-Z][a-z]+[A-Z]$'
    
    # re.sub replaces the matched suffix with an empty string
    base = re.sub(pattern, '', text)
    return base

def list_broad_matches(target_value: str, pool_of_options: set) -> list:
    """
    Takes a specific string, finds its base, and returns all 
    items in the option pool that start with that same base.
    """
    base = get_base_pattern(target_value)
    # print(f"Original: {target_value} -> Isolated Base: {base}")
    
    # Find everything in your JSON pools that starts with the same prefix
    matches = [item for item in pool_of_options if item.startswith(base)]
    return matches

def reporting_summary(errors_found: bool):
    # Final reporting
    print("--- Validation Summary ---")
    if errors_found:
        print("❌ Validation failed with errors.\n")
    else:
        print("✅ All integrity checks passed successfully!\n")


def filter_list(names_list, pattern):
    return [name for name in names_list if pattern in name]

def strip_comments(match):
    item = match.group(1)
    if item.startswith("/") or item.startswith("#"):
        return ""  # It's a comment, delete it
    return item  # It's a string literal, keep it

def load_json_with_comments(file):
    content = file.read()

    # Regex to match syntax like /* comments */ and // comments
    pattern = r"((?:\"(?:\\.|[^\"])*\"|' (?:\\.|[^'])*')|(?:\/\*(?:[^*]|\*(?!\/))*\*\/|\/\/.*))"


    clean_content = re.sub(pattern, strip_comments, content)
    return json.loads(clean_content)

def scan_images(base_dir, images_dir) -> list[str]:
    # Safety checks
    if not images_dir.exists():
        print(f"Error: Image directory '{images_dir}' does not exist.")
        return []

    file_list = []
    image_files = images_dir.rglob("*.png")
    for file_name in image_files:
        # Reconstruct the portrait image path using forward slashes, remove images prefix
        # e.g., 'paperdoll/bodyNewSkinPubes/NewSkinPubesB'
        path = f"{file_name}".replace(f"{base_dir}/images/", '').replace('.png', '')
        file_list.append(path)
    
    print(f"Found {len(file_list)} image files in '{images_dir}'")
    return file_list

def auto_crop_image(input_path, output_path, fuzz_percent=10, margin=20):
    """Crops the background content of an image using ImageMagick and adds a transparent margin.

    Args:
        input_path (str): Path to the source image.
        output_path (str): Path where the cropped image will be saved (must support alpha, e.g. PNG).
        fuzz_percent (int): Color variation tolerance percentage (0-100).
        margin (int or str): Margin in pixels (e.g., 20 or "30x10").
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        return False

    command = [
        "magick",
        input_path,
        "-fuzz",
        f"{fuzz_percent}%",
        "-trim",
        "+repage",
        "-bordercolor",
        "none",  # Sets the border color to transparent
        "-border",
        str(margin),
        output_path,
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Success: Cropped image saved to '{output_path}'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running ImageMagick: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: 'magick' command not found. Please install ImageMagick.")
        return False

def create_item_icon(
    input_path, output_path, fuzz_percent=10, background="none"
):
    """Trims an image and resizes/pads it into a centered 16x16 image.

    Args:
        input_path (str): Path to the source image.
        output_path (str): Output path (should end in .png or .ico for transparency).
        fuzz_percent (int): Variation tolerance for the initial auto-crop.
        background (str): Padding color ('none' for transparent, or 'white', 'black', etc.).
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        return False

    command = [
        "magick",
        input_path,
        "-fuzz",
        f"{fuzz_percent}%",
        "-trim",
        "+repage",
        # Fit content inside 16x16 while keeping aspect ratio
        "-resize",
        "16x16",
        # Set canvas background color and gravity for centering
        "-background",
        str(background),
        "-gravity",
        "center",
        # Pad canvas out to exactly 16x16
        "-extent",
        "16x16",
        output_path,
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Success: 16x16 icon saved to '{output_path}'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running ImageMagick: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: 'magick' command not found. Please install ImageMagick.")
        return False

def resolve_depend_dir() -> Path | None:
    props_path = Path("NewSkinPatch/Config.Build.user.props")
    if not props_path.exists():
        print(f"Warning: Config.Build.user.props not found at '{props_path}'. Skipping base game asset checks.")
        return None

    props_text = props_path.read_text(encoding="utf-8")
    match = re.search(r"<DependsDir>*(.*?)</DependsDir>", props_text, re.IGNORECASE | re.DOTALL)
    if match is None:
        print(f"Warning: <DependsDir> not found in '{props_path}'.")
        return None

    depend_dir = Path(match.group(1).strip())
    if not depend_dir.is_absolute():
        depend_dir = (props_path.parent.parent / depend_dir).resolve()

    return depend_dir
