"""Remove only Labelme imageData; preserve every other field and formatting."""
from pathlib import Path
import json
import re
import sys

def clean(path):
    original = path.read_bytes()
    text = original.decode("utf-8-sig")
    data = json.loads(text)
    if not isinstance(data, dict) or not data.get("imageData"):
        return False
    if "shapes" not in data or "imagePath" not in data:
        raise ValueError(f"Not a Labelme annotation: {path}")
    expected = dict(data, imageData=None)
    updated, count = re.subn(r'("imageData"\s*:\s*)"(?:[^"\\]|\\.)*"', r'\1null', text)
    if count != 1 or json.loads(updated) != expected:
        raise ValueError(f"Cannot safely remove imageData: {path}")
    if "--check" in sys.argv:
        raise ValueError(f"Embedded image found: {path}; run python strip_image_data.py")
    path.write_bytes((b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b"") + updated.encode("utf-8"))
    return True

if __name__ == "__main__":
    count = sum(clean(p) for p in Path(__file__).resolve().parent.glob("*.json"))
    print(f"Removed embedded images from {count} JSON files")
