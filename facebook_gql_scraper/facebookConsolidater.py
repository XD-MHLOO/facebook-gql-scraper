import json
from copy import deepcopy


def merge(target, patch):
    """Recursively merge dictionaries, extend lists."""
    if isinstance(target, dict) and isinstance(patch, dict):
        for key, value in patch.items():
            if key in target:
                if isinstance(target[key], list) and isinstance(value, list):
                    target[key].extend(deepcopy(value))
                else:
                    target[key] = merge(target[key], value)
            else:
                target[key] = deepcopy(value)
        return target
    return deepcopy(patch)


def apply_patch(result, path, patch_data):
    """Apply a deferred/incremental patch to the result."""

    if not path:
        return merge(result, patch_data)

    current = result

    # Navigate to parent of destination
    for i, key in enumerate(path[:-1]):
        next_key = path[i + 1] if i + 1 < len(path) else None
        is_list = isinstance(next_key, int)

        if isinstance(current, dict):
            if key not in current:
                current[key] = [] if is_list else {}
            current = current[key]

        elif isinstance(current, list):
            if not isinstance(key, int):
                raise TypeError(f"List requires integer index, got {key}")

            if len(current) <= key:
                current.extend([[] if is_list else {}] * (key - len(current) + 1))
            current = current[key]

        else:
            raise TypeError(
                f"Cannot navigate path at {key}. Current type: {type(current)}"
            )

    # Apply patch at final location
    last_key = path[-1]

    if isinstance(current, dict):
        if last_key in current:
            current[last_key] = merge(current[last_key], patch_data)
        else:
            current[last_key] = deepcopy(patch_data)

    elif isinstance(current, list):
        if not isinstance(last_key, int):
            raise TypeError("List requires integer index")

        if len(current) <= last_key:
            current.extend([None] * (last_key - len(current) + 1))

        if current[last_key] is None:
            current[last_key] = deepcopy(patch_data)
        else:
            current[last_key] = merge(current[last_key], patch_data)

    return result


def consolidate_jsonl(raw_text: str):
    """Parse a JSONL string and consolidate base + deferred patches.

    Returns the merged dict, or None if no base response was found.
    """

    base = None
    patches = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"Invalid JSONL: {e}")
            return None

        if isinstance(data, dict) and "path" in data and "data" in data:
            patches.append(data)
        elif base is None:
            base = data

    if base is None:
        print("No base response found")
        return None

    result = deepcopy(base)

    for i, patch in enumerate(patches):
        path = patch.get("path", [])
        patch_data = patch.get("data")

        try:
            result = apply_patch(result, path, patch_data)
        except Exception as e:
            print(f"Failed to apply patch #{i}: path={path}, error={e}")

    return result


def consolidate_file(file_path):
    """Read a JSONL file and consolidate it. Thin wrapper around consolidate_jsonl."""
    with open(file_path, "r", encoding="utf-8") as input_f:
        return consolidate_jsonl(input_f.read())


if __name__ == "__main__":
    consolidated = consolidate_file("facebook.json")

    if consolidated is not None:
        with open("facebook2.json", "w", encoding="utf-8") as f:
            json.dump(consolidated, f, indent=2, ensure_ascii=False)

        print("Consolidated data written to facebook2.json")
