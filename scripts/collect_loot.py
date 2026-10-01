import glob
import json
import os
from pathlib import Path
from utilities import safely_write_json, filter_list


def unique_in_order(items: list[str]) -> list[str]:
    """Return items in first-seen order without duplicates."""
    seen: set[str] = set()
    unique_items: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    return unique_items


def extract_str_names(file_path: str) -> list[str]:
    # Open the file in read mode
    with open(file_path, 'r', encoding='utf-8') as file:
        # Load the JSON data into a Python list of dictionaries
        data = json.load(file)

    # Extract the 'strName' values
    # The 'if "strName" in item' check prevents errors if a dictionary is missing the key
    names = [item["strName"] for item in data if "strName" in item]

    return names


def join_names(names_list: list[str]) -> str:
    # The .join() method glues everything in the list together using the separator string
    return "|".join(names_list)


def loot_string(loot_list: list[str]) -> str:
    unique_loot = unique_in_order(loot_list)
    if not unique_loot:
        return ""

    chance = round(0.95 / len(unique_loot), 2)
    loot_collected: list[str] = []
    for loot_name in unique_loot:
        loot_collected.append(f"{loot_name}={chance}x1")
    return "|".join(loot_collected)


def generate_collections(loot_origin: list[str], loot_stash: str) -> None:
    origin_files = []
    for pattern in loot_origin:
        origin_files.extend(glob.glob(pattern))

    loot_collected: list[str] = []
    for file in origin_files:
        loot_collected.extend(extract_str_names(file))

    # Iterate through all loot items
    glasses = unique_in_order(filter_list(loot_collected, "Glasses"))

    # hardcoded base CO
    glasses.append("ItmGlassesOrange")

    glasses = unique_in_order(glasses)

    print(f"Collected {len(glasses)} glasses")

    out = [{
        "strName": "RandomGlasses",
        "aCOs": [loot_string(glasses)],
        "strType": "item"
    }]

    safely_write_json(loot_stash, out, True)

if __name__ == "__main__":
    loot_files = [
        "data/loot/loot_self_*.json",
    ]
    out_file = "data/loot/loot_glasses.json"

    generate_collections(loot_files, out_file)
