#!/usr/bin/env python3
"""Generate cooverlay and slot_effects JSON templates for directory images."""

import argparse
import json
import glob
import os
import shutil
from typing import Set
from pathlib import Path
import re

from utilities import auto_crop_image, create_item_icon, safely_write_json
from collect_loot import generate_collections

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
            "strDescTemplate": "{colour} Glasses pattern {pattern} - minimum protection when staring at the sun.",
        }
    }

    body_base_image = "paperdoll/bodyGlassesBlank.png"

    all_overlays = []
    all_slots = []
    loot = []
    loot_names = []

    pattern = r"^.*pbase(Glasses)([A-Z0-9]*)$"

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

        if "images" not in folder_path.parts:
            print(f"Error: The folder '{target_folder}' is not inside an images directory.")
            continue

        images_index = len(folder_path.parts) - 1 - folder_path.parts[::-1].index("images")
        image_folder = Path(*folder_path.parts[images_index:])

        # Iterate through all files in the directory (skipping subdirectories)
        for file_path in sorted(folder_path.iterdir(), reverse=False):
            if file_path.is_file():
                # Extract the filename without the extension (e.g., 'NewSkinPubesB')
                file_name = file_path.stem

                match = re.fullmatch(pattern, file_name)
                if not match:
                    continue

                pattern_label = match.group(2)
                kind = match.group(1)

                if "01" in pattern_label:
                    continue  # Skip the base pattern, it's empty

                item_name = f"Itm{kind}{pattern_label}"
                slot_name = f"Body{kind}{pattern_label}"

                portrait_img = f"paperdoll/port{kind}{pattern_label}"
                body_img = f"paperdoll/body{kind}{pattern_label}"

                # The base image is a handle that allows to pick up the item - it just has 1% opacity, so it is invisible.
                if not Path(body_base_image).exists():
                    print(f"creating: {body_img} from {body_base_image}")
                    body_img_actual = f"images/{body_img}.png"
                    source = Path(f"images/{body_base_image}")
                    if source.exists():
                        shutil.copy2(source, body_img_actual)
                    else:
                        print(f"Error: The source image '{source.as_posix()}' does not exist.")

                port_img_actual = f"images/{portrait_img}.png"
                if not Path(port_img_actual).exists():
                    print(f"creating: {portrait_img} from {file_path.as_posix()}")
                    
                    done = auto_crop_image(file_path, port_img_actual)
                    if not done:
                        print(f"Error: Failed to auto-crop the image '{file_path.as_posix()}'.")

                item_icon = f"items/{item_name}"
                item_icon_actual = f"images/{item_icon}.png"
                if not Path(item_icon_actual).exists():
                    print(f"creating: {item_icon} from {file_path.as_posix()}")
                    done = create_item_icon(file_path, item_icon_actual)
                
                # Collect loot names for generating loot collections later
                loot_names.append(item_name)

                # Construct CondOverlay and SlotEffect based on the kind
                ref = master_ref.get(kind, master_ref["Glasses"])

                colour = ""

                short_name = ref["strNameShortTemplate"].format(colour=colour, item_kind=kind, pattern=pattern_label)
                friendly_name = ref["strNameFriendlyTemplate"].format(
                    colour=colour,
                    item_kind=kind,
                    pattern=pattern_label
                ).strip()

                desc = ref["strDescTemplate"].format(
                    colour=colour,
                    colour_lower=colour.lower(),
                    item_kind=kind,
                    pattern=pattern_label,
                    file_name=file_name,
                ).strip()

                new_slots = ref["mapSlotEffects"].copy()
                new_slots.append(slot_name)
                overlay_obj = {
                    "strName": item_name,
                    "strNameShort": short_name,
                    "strDesc": desc,
                    "strNameFriendly": friendly_name,
                    "strCOBase":  ref["strCOBase"],
                    "strImg": item_icon,
                    "strImgNorm": ref["strImgNorm"].replace("Orange", colour),
                    "strPortraitImg": portrait_img,
                    "strCondLoot": ref["strCondLoot"],
                    "mapSlotEffects": new_slots,
                    "mapModeSwitches": []
                }

                all_overlays.append(overlay_obj)

                slot_effect = {
                    "strName": slot_name,
                    "strSlotImage": body_img,
                    "strSlotImageUnder": None,
                    "strIASlot": ref["strIASlot"],
                    "strIAUnslot": ref["strIAUnslot"],
                    "strIASlotParents": None,
                    "strIAUnslotParents": None,
                    "mapMeshTextures": []
                }
                if ref["meshTexture"] is not None:
                    slot_effect["mapMeshTextures"] = [
                        "Outfit01", ref["meshTexture"]
                    ]

                all_slots.append(slot_effect)

                # create loot reference for each item, with a 1.0x1 chance of dropping
                new_loot = {
                    "strName": f"{item_name}",
                    "aCOs": [f"{item_name}=1.0x1"],
                    "strType": "item"
                }
                loot.append(new_loot)

    if not all_overlays:
        print("No files found to process.")
        return

    safely_write_json(output_cooverlays, all_overlays, preserve)
    safely_write_json(output_slots, all_slots, preserve) # there is a base CO slot_effect there
    safely_write_json(output_loot, loot, preserve)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="List images in a directory and create cooverlay/slot_effects JSON."
    )
    
    parser.add_argument("dir", type=str, help="Directory containing images")
    args = parser.parse_args()

    loot_files = "data/loot/loot_self_reference.json"

    generate_overlay_json(args.dir, "data/cooverlays/cooverlays_glasses.json", "data/slot_effects/slot_effects_glasses.json", loot_files, preserve=True)

    generate_collections(glob.glob(loot_files), "data/loot/loot_glasses.json")
