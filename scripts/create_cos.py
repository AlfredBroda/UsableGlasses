#!/usr/bin/env python3
"""Generate cooverlay and slot_effects JSON templates for directory images."""

import argparse
import json
import glob
import os
from typing import Set
from pathlib import Path
import re


IMAGE_EXTENSION = ".png"

def generate_overlay_json(target_folders: str, output_cooverlays: str, output_slots: str, output_loot: str, preserve=True):
    master_ref = {
        "Glasses": {
            "strCOBase": "ItmGlassesOrange",
            "mapSlotEffects" : [
                "heldL","HeldItmDefaultL",
                "heldR","HeldItmDefaultR",
                "head_glasses"
            ],
            "strIASlot": None,
            "strIAUnslot": None,
            "meshTexture": None,
            "strImg": "items/ItmGlassesOrange",
            "strImgNorm": "items/ItmGlassesOrangeN",
            "strCondLoot": "CNDOLGlasses",
            "strNameShortTemplate": "{colour} Glasses",
            "strNameFriendlyTemplate": "Glasses: {pattern} {colour}",
            "strDescTemplate": "{colour} Glasses of a {pattern_lower} - minimum protection when staring at the sun.",
        }
    }
    all_overlays = []
    all_slots = []
    loot = []
    loot_names = []

    pattern = r"^.*(pbase)Glasses([A-Z0-9]*)$"

    # Convert string path to Path object
    folders = glob.glob(target_folders)
    if not folders:
        print(f"Error: No files found matching the pattern '{target_folders}'.")
        return

    for target_folder in folders:
        folder_path = Path(target_folder)

        if not folder_path.exists():
            print(f"Error: The folder '{target_folder}' does not exist.")
            continue

        # Iterate through all files in the directory (skipping subdirectories)
        for file_path in sorted(folder_path.iterdir(), reverse=True):
            if file_path.is_file():
                # Extract the filename without the extension (e.g., 'NewSkinPubesB')
                file_name = file_path.stem

                match = re.fullmatch(pattern, file_name)
                if not match:
                    print(f" Skipping file '{file_name}' as it does match the variation pattern.")
                    continue

                print(f" Processing file '{file_name}'...")

                pattern_label = match.group(2)
                kind = "Glasses"  # Default kind

                cleaned = re.sub(r"^port", "", file_name)  # ^ ensures it only matches at the start
                cleaned = re.sub(r"^body", "", cleaned) 
                sanitized_name = cleaned.replace("_", "").replace(" ", "").replace("NewSkin", "").strip()
                # sanitized_folder = folder_path.name.replace("_", "").replace(" ", "")

                # Dynamic naming based on your template
                # Assumes 'NewSkinPubesB' format to derive 'NSPubesB' and others
                short_name = (
                    "".join([c for c in file_name if c.isupper()])
                    if len(file_name) > 10
                    else file_name
                ).strip()

                # Construct CondOverlay and SlotEffect based on the kind
                ref = master_ref.get(kind, master_ref["Glasses"])  # Defaulting to 'Panties' just to make compiler happy, but this should never happen due to the earlier check.

                # Reconstruct the portrait image path using forward slashes, remove images prefix
                # e.g., 'paperdoll/clothing/Undergarments/paroxysm2049/Floral Hawaiian Blue/portFloralHawaiianBlueNewSkinSportsBra'
                portrait_path = f"{folder_path.as_posix()}/{file_name}".replace('images/', '').replace('NewSkin_Clothing_Addon/', '')
                # item_name = f"OutfitNewSkin{sanitized_folder}{sanitized_name}"
                # slot_name = f"Slot{sanitized_folder}{cleaned}"

                item_name = f"ItmGlasses{sanitized_name}"
                slot_name = f"BodyGlasses{cleaned}"
                pattern_label_for_desc = pattern_label.lower().strip()

                loot_names.append(item_name)

                colour = ""
                item_label = "Glasses"    

                short_name = ref["strNameShortTemplate"].format(colour=colour, item_kind=item_label)
                friendly_name = ref["strNameFriendlyTemplate"].format(
                    colour=colour,
                    item_kind=item_label,
                    pattern=pattern_label
                )
                if colour in pattern_label:
                    friendly_name = friendly_name.replace(f" {colour}", "").rstrip()
                elif friendly_name.endswith(f" {colour}") and pattern_label.lower() == "plain":
                    friendly_name = friendly_name.replace(f" {colour}", "")
                    friendly_name = friendly_name.rstrip()
                desc = ref["strDescTemplate"].format(
                    colour=colour,
                    colour_lower=colour.lower(),
                    item_kind=item_label,
                    pattern=pattern_label,
                    pattern_lower=pattern_label_for_desc,
                    file_name=file_name,
                )

                new_slots = ref["mapSlotEffects"].copy()
                new_slots.append(slot_name)
                overlay_obj = {
                    "strName": item_name,
                    "strNameShort": short_name,
                    "strDesc": desc,
                    "strNameFriendly": friendly_name,
                    "strCOBase":  ref["strCOBase"],
                    "strImg": ref["strImg"].replace("White", colour),
                    "strImgNorm": ref["strImgNorm"].replace("White", colour),
                    "strPortraitImg": portrait_path,
                    "strCondLoot": ref["strCondLoot"],
                    "mapSlotEffects": new_slots,
                    "mapModeSwitches": []
                }

                all_overlays.append(overlay_obj)

                slot_effect = {
                    "strName": slot_name,
                    "strSlotImage": portrait_path,
                    "strSlotImageUnder": None,
                    "strIASlot": ref["strIASlot"],
                    "strIAUnslot": ref["strIAUnslot"],
                    "strIASlotParents": None,
                    "strIAUnslotParents": None,
                    "mapMeshTextures": [
                        "Outfit01", ref["meshTexture"]
                    ]
                }
                all_slots.append(slot_effect)

                # create loot reference for each item, with a 1.0x1 chance of dropping
                new_loot = {
                    "strName": f"Itm{item_name}",
                    "aCOs": [f"{item_name}=1.0x1"],
                    "strType": "item"
                }
                loot.append(new_loot)

    if not all_overlays:
        print("No files found to process.")
        return

    safely_write_json(output_cooverlays, all_overlays, preserve)
    safely_write_json(output_slots, all_slots, preserve)
    safely_write_json(output_loot, loot, preserve)


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

def filter_list_formatted(names_list, pattern) -> list[str]:
    return [("{"+name).replace(",","},") for name in names_list.splitlines() if pattern in name]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="List images in a directory and create cooverlay/slot_effects JSON."
    )
    
    parser.add_argument("dir", type=str, help="Directory containing images")
    args = parser.parse_args()

    generate_overlay_json(args.dir, "data/cooverlays/cooverlays_glasses.json", "data/slot_effects/slot_effects_glasses.json", "data/loot/loot_self_reference.json", preserve=True)

