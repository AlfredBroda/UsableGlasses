import json
import glob
import sys
from typing import Dict, Set, List, Union
from utilities import reporting_summary, load_json_files, list_broad_matches, safely_write_json

def validate_slot_effects_map(item: dict, item_name: str, slot_effects: Set[str], used_slot_effects: Dict[str, str], field_label: str = "mapSlotEffects[1]") -> bool:
    """
    Validates mapSlotEffects array in an item (overlay or condowner).
    Returns True if errors found.
    """
    errors_found = False
    slot_effects_map = item.get("mapSlotEffects")
    if slot_effects_map and isinstance(slot_effects_map, list):
        # Ensure the array has at least 2 elements
        if len(slot_effects_map) >= 2:
            target_slot_effect = match_slot(slot_effects_map)
            if target_slot_effect is None:
                print(f"[{item_name}]: No valid slot entry found in 'mapSlotEffects'.")
                errors_found = True
            else:
                # Check existence in slot files
                if target_slot_effect not in slot_effects:
                    print(f"[{item_name}]: '{field_label}' value '{target_slot_effect}' not found in Slot files.")
                    errors_found = True
                
                # Enforce strict 1:1 uniqueness mapping
                if target_slot_effect in used_slot_effects:
                    print(f"[{item_name}]: 1:1 Violation! '{field_label}' value '{target_slot_effect}' is already assigned to item '{used_slot_effects[target_slot_effect]}'.")
                    errors_found = True
                else:
                    used_slot_effects[target_slot_effect] = item_name
        else:
            print(f"[{item_name}]: 'mapSlotEffects' array has fewer than 2 elements.")
            errors_found = True
    
    return errors_found

def validate_overlays(condowners_file: str = "condowners_skinA.json", slot_effects_file: str = "slot_effects_skinA.json", overlay_file: str = "cooverlays_body_skinA.json", 
                      loot_files: str = "loot.json", add_loot: Union[str, bool] = False):
    # 1. Load the valid target keys from CO and Slot files
    print("Loading reference data...")
    co_bases = load_json_files(condowners_file, "strName")
    co_bases.add("ItmTShirt01")  # Allow base game tshirt expansion
    co_bases.add("ItmShoe01L")  # Allow base game shoe expansion
    co_bases.add("ItmShoe01R")  # Allow base game shoe expansion
    co_bases.add("OutfitHelmet02")  # Allow base game helmet expansion

    slot_effects = load_json_files(slot_effects_file, "strName")
    loot_names = load_json_files(loot_files, "strName")
    
    overlay_files = glob.glob(overlay_file)
    if not overlay_files:
        print(f"Error: No overlay files found matching '{overlay_file}'\n")
        return True

    errors_found = False
    
    # Track slot effect targets for 1:1 validation across all overlays
    used_slot_effects: Dict[str, str] = {} # slot_effect_name -> overlay_name

    new_loot: list[dict] = []
    print(f"Starting validation of {overlay_file}...")
    for file_path in overlay_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                overlays = data if isinstance(data, list) else [data]
                
            for index, overlay in enumerate(overlays):
                if not isinstance(overlay, dict):
                    continue
                
                # Get an identifier for error reporting
                overlay_name = overlay.get("strName", f"Index {index} in {file_path}")

                if overlay_name not in loot_names:
                    if add_loot:
                        print(f"? [{overlay_name}]: missing self reference in Loot files - creating.")
                        # Create a new LootItem instance
                        item = {
                            "strName": overlay_name,
                            "aCOs": [f"{overlay_name}=1.0x1"],
                            "strType": "item"
                        }
                        new_loot.append(item)
                    else:
                        print(f"? [{overlay_name}]: missing self reference in Loot files!")

                # --- Validate Many-to-One: strCOBase -> CO files ---
                co_base = overlay.get("strCOBase")
                if not co_base:
                    print(f"[{overlay_name}]: Missing 'strCOBase' field.")
                    errors_found = True
                elif co_base not in co_bases:
                    print(f"[{overlay_name}]: 'strCOBase' value '{co_base}' not found in CO files.")

                    alt = list_broad_matches(co_base, co_bases)
                    if alt:
                        print(f"  Possible alternatives in CO files: {', '.join(alt)}")
                    else:
                        print("  No close matches found in CO files.")
                    errors_found = True
                
                # --- Validate One-to-One: mapSlotEffects [1] -> Slot files ---
                errors_found |= validate_slot_effects_map(overlay, overlay_name, slot_effects, used_slot_effects, "mapSlotEffects[1]")

                condition = overlay.get("strCondLoot")
                if not condition:
                    continue
                elif condition not in loot_names:
                    print(f"❌ [{overlay_name}]: 'strCondLoot' value '{condition}' not found in Loot files.")
                    errors_found = True

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error parsing overlay file {file_path}: {e}")
            errors_found = True
    reporting_summary(errors_found)

    if add_loot and len(new_loot) > 0:
        safely_write_json(add_loot, new_loot, True)

    return errors_found

def validate_items(condowner_file: str, items_file: str):
    """
    Validates that all COs have corresponding entries in the item files.
    """
    errors_found = False
    print(f"Starting validation of 'strItemDef' in {condowner_file}...")
    try:
        with open(condowner_file, 'r', encoding='utf-8') as f:
            condowner_refs = load_json_files(condowner_file, "strItemDef")
            with open(items_file, 'r', encoding='utf-8') as i:
                item_names = load_json_files(items_file, "strName")
                for item in condowner_refs:
                    if item not in item_names:
                        print(f"Error: CO ref '{item}' does not have a corresponding entry in the item files.")
                        errors_found = True
    except FileNotFoundError:
        print("The file could not be found.")

    reporting_summary(errors_found)

    return errors_found

def validate_condowners(condowner_file: str = "condowners_skinA.json", slot_effects_file: str = "slot_effects_skinA.json", 
                        loot_files: str = "loot.json", add_loot: Union[str, bool] = False):
    # 1. Load the valid target keys from CO and Slot files
    print("Loading reference data...")
    slot_effects = load_json_files(slot_effects_file, "strName")
    loot_names = load_json_files(loot_files, "strName")
  
    errors_found = False
    
    # Track slot effect targets for 1:1 validation across all condowners
    used_slot_effects: Dict[str, str] = {} # slot_effect_name -> condowner_name

    new_loot: List[dict] = []
    print(f"Starting validation of {condowner_file}...")
    try:
        with open(condowner_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            condowners = data if isinstance(data, list) else [data]
            
        for index, co in enumerate(condowners):
            if not isinstance(co, dict):
                continue
            
            # Get an identifier for error reporting
            co_name = co.get("strName", f"Index {index} in {condowner_file}")
            if co_name not in loot_names:
                if add_loot:
                    print(f"? [{co_name}]: missing self reference in Loot files - creating.")
                    # Create a new LootItem instance
                    item = {
                        "strName": co_name,
                        "aCOs": [f"{co_name}=1.0x1"],
                        "strType": "item"
                    }
                    new_loot.append(item)
                else:
                    print(f"? [{co_name}]: missing self reference in Loot files!")
            
            # --- Validate One-to-One: mapSlotEffects [1] -> Slot files ---
            errors_found |= validate_slot_effects_map(co, co_name, slot_effects, used_slot_effects, "mapSlotEffects[]")
            condition = co.get("strCondLoot")
            if not condition:
                continue
            elif condition not in loot_names:
                print(f"❌ [{co_name}]: 'strCondLoot' value '{condition}' not found in Loot files.")
                errors_found = True

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error parsing condowners file {condowner_file}: {e}")
        errors_found = True
    reporting_summary(errors_found)

    if add_loot and len(new_loot) > 0:
        safely_write_json(add_loot, new_loot, True)

    return errors_found

def match_slot(slot_effects_map):
    for name, content in zip(slot_effects_map[0::2], slot_effects_map[1::2]):
        if name not in ignored_slots:
            # print(f"Found valid slot: {name}")
            return content

    return None

ignored_slots = ["heldL", "heldR"]

if __name__ == "__main__":
    got_errors = False

    # Validate items for each skin type
    items_validations = [
        ("data/condowners/condowners_glasses.json", "data/items/items_glasses.json"),
    ]
    for condowner_file, items_file in items_validations:
        got_errors |= validate_items(condowner_file=condowner_file, items_file=items_file)

    # Validate condowners slot effects for each skin type
    condowner_validations = [
        ("data/condowners/condowners_glasses.json", "data/slot_effects/slot_effects_glasses.json"),
    ]
    for condowner_file, slot_effects_file in condowner_validations:
        got_errors |= validate_condowners(condowner_file=condowner_file, slot_effects_file=slot_effects_file, 
                                          loot_files="data/loot/loot*.json", add_loot="data/loot/loot_self_reference.json")

    co_file = "data/condowners/condowners_*.json"
    overlay_validations = [
        ("data/cooverlays/cooverlays_socks.json", "data/slot_effects/slot_effects_clothes.json"),
    ]
    for overlay_file, slot_effects_file in overlay_validations:
        got_errors |= validate_overlays(condowners_file=co_file, slot_effects_file=slot_effects_file, overlay_file=overlay_file, 
                                        loot_files="data/loot/loot*.json", add_loot="data/loot/loot_self_reference.json")

    if got_errors:
        print("❌ One or more validation checks failed. Please review the errors above.")
        sys.exit(1)
