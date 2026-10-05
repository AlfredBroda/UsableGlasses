import glob
import json
import re
import sys
from pathlib import Path
from utilities import filter_list_formatted, filter_list, scan_images, auto_crop_image, resolve_depend_dir

exception_list = [
    "Crew2Base"
]

def missing_image_check(ref_field, image_file_list, json_files, suffixes=[""], filter="") -> bool:
    json_content = ""
    for json_file in json_files:
        json_path = Path(json_file)
        if not json_path.exists():
            print(f"Error: JSON reference file missing at '{json_path}'")
            return True

        # Replicating bash grep: Read the entire JSON file as raw text once
        print(f"Loading '{json_path}' for cross-checking...")
        json_content += "\n" + json_path.read_text(encoding="utf-8")

    if ref_field == "mapMeshTextures":
        print(f"Scanning files for '{ref_field}' as map without filter...")
        image_data = filter_map(json_content, ref_field)
    else:
        ref_list = filter_list_formatted(json_content, ref_field)

        if filter != "":
            print(f"Scanning files for '{ref_field}' with filter '{filter}'...")
            ref_list = filter_list(ref_list, filter)
        else:
            print(f"Scanning files for '{ref_field}'...")

        image_paths = "".join(ref_list)
        try:
            image_data = json.loads(f"[{image_paths}]".replace(",]","]"))
            # Ensure the  data is a list
            if not isinstance(image_data, list):
                print(f"Warning: image_data is not a list. Aborting.")
                return True
        except json.JSONDecodeError:
            print(image_paths)
            print(f"Warning: image_data was corrupted or not valid JSON. Aborting.")
            return True

    skip_count = 0
    checked_count = 0
    match_count = 0
    crops = 0

    for image_path in image_data:
        if ref_field not in image_path:
            continue

        path = image_path[ref_field]
        if path == "" or path == "blank" or path == None:
            checked_count += 1
            match_count += 1
            continue

        for suffix in suffixes:
            checked_count += 1

            to_match = f"{path}{suffix}"
            if to_match in image_file_list or to_match in exception_list:
                match_count += 1
            else:
                print(f" ❌ Not found {ref_field}: {to_match}")
                if ref_field == "strPortraitImg":
                    p_name = replace_prefix(to_match, "port", "body")
                    prospect = Path(base_dir/"images"/f"{p_name}.png")
                    exists = prospect.exists()
                    print(f"  crop candidate: {prospect}\n  exists: {exists}")
                    if exists:
                        dest = Path(base_dir/"images"/f"{to_match}.png")
                        done = auto_crop_image(prospect, dest)
                        if done:
                            crops += 1
                        else:
                            skip_count += 1
                    else:
                        skip_count += 1
                else:
                    skip_count += 1

    print(f"Matched: {match_count}/{checked_count} from {len(image_data)} base references | Missing: {skip_count}, Generated: {crops} files\n")
    if skip_count == 0:
        return False
    else:
        print(f"❌ {skip_count} files are missing. Please review the errors above.\n")
        return True

def filter_map(json_content: str, ref_field: str) -> list[dict[str, str]]:
    image_data = []
    pattern = rf'"{re.escape(ref_field)}"\s*:\s*(\[[^\]]*\])'

    for match in re.finditer(pattern, json_content):
        mesh_textures = json.loads(match.group(1))
        if not isinstance(mesh_textures, list):
            continue
        image_data.extend(
            {ref_field: image_path.strip()}
            for texture_paths in mesh_textures[1::2]
            if isinstance(texture_paths, str)
            for image_path in texture_paths.split(":")
            if image_path.strip()
        )

    return image_data

def replace_prefix(filepath: str | Path, prefix: str, repl: str) -> Path:
    path = Path(filepath)
    filename = path.name  # e.g., "portShirt01.png"
    
    if filename.startswith(prefix):
        new_filename = repl + filename[len(prefix):]  # Slice off 'port', prepend 'body'
        return path.with_name(new_filename)
    
    return path

if __name__ == "__main__":
    files = []
    base_dir = Path(".")
    got_errors = False

    # Addon image list
    image_file_list = scan_images(base_dir, base_dir/"images")
    for i, image_path in enumerate(image_file_list):
        print(f"Image {i+1}/{len(image_file_list)}: {image_path}")

    print(f"\nChecking {base_dir.name} cooverlays references...")
    # Port images, displayed in the MTT on the right
    files = glob.glob(str(base_dir/"data"/"cooverlays"/"cooverlays_*.json"))

    got_errors |= missing_image_check(ref_field="strImg",image_file_list=image_file_list, json_files=files)
    got_errors |= missing_image_check(ref_field="strImgNorm", image_file_list=image_file_list, json_files=files)
    got_errors |= missing_image_check(ref_field="strImgDamaged", image_file_list=image_file_list, json_files=files)
    got_errors |= missing_image_check(ref_field="strPortraitImg", image_file_list=image_file_list, json_files=files)

    # The actual large paperdoll images
    print(f"\nChecking {base_dir.name} slot_effects references...")
    files = glob.glob(str(base_dir/"data"/"slot_effects"/"slot_effects_*.json"))

    got_errors |= missing_image_check(ref_field="strSlotImage", image_file_list=image_file_list, json_files=files)
    got_errors |= missing_image_check(ref_field="mapMeshTextures", image_file_list=image_file_list, json_files=files)

    print(f"\nChecking {base_dir.name} items references...")
    image_file_list = scan_images(base_dir, base_dir/"images"/"items")
    files = glob.glob(str(base_dir/"data"/"items"/"items_*.json"))

    got_errors |= missing_image_check(ref_field="strImgDamaged", image_file_list=image_file_list, json_files=files)
    got_errors |= missing_image_check(ref_field="strImgNorm", image_file_list=image_file_list, json_files=files)
    got_errors |= missing_image_check(ref_field="strImg", image_file_list=image_file_list, json_files=files)

    if got_errors:
        print("❌ One or more validation checks failed. Please review the errors above.")
        sys.exit(1)
    else:
        print("✅ All image references matched successfully.")
        sys.exit(0)
