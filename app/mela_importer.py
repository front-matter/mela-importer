#!/usr/bin/env python3
"""
Mela → Mealie bulk importer
"""

import json
import sys
import zipfile
import base64
import tempfile
import os
import requests

MEALIE_URL = os.environ["MEALIE_URL"]
MEALIE_API_KEY = os.environ["MEALIE_API_KEY"]

HEADERS = {
    "Authorization": f"Bearer {MEALIE_API_KEY}",
    "Content-Type": "application/json",
}


def parse_mela(data: dict) -> dict:
    """Convert a melarecipe dict to Mealie PATCH payload."""

    # Split newline-separated ingredients, skip empty lines and group headers (#)
    ingredients = []
    for line in data.get("ingredients", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        ingredients.append(
            {
                "note": line,
                "isFood": False,
                "disableAmount": True,
                "quantity": 0,
            }
        )

    # Split newline-separated instructions, skip empty lines
    instructions = []
    for line in data.get("instructions", "").split("\n"):
        line = line.strip()
        if line:
            instructions.append({"text": line})

    # Categories
    categories = [{"name": c} for c in data.get("categories", [])]

    # Notes
    notes = []
    if data.get("notes"):
        notes.append({"title": "", "text": data["notes"]})
    if data.get("nutrition"):
        notes.append({"title": "Nutrition", "text": data["nutrition"]})

    return {
        "name": data.get("title", "Untitled"),
        "description": data.get("text", ""),
        "recipeYield": data.get("yield", ""),
        "prepTime": data.get("prepTime", ""),
        "cookTime": data.get("cookTime", ""),
        "totalTime": data.get("totalTime", ""),
        "orgURL": data.get("link", ""),
        "recipeIngredient": ingredients,
        "recipeInstructions": instructions,
        "recipeCategory": categories,
        "notes": notes,
    }


def upload_image(slug: str, b64_image: str):
    """Upload a base64 image to a Mealie recipe."""
    try:
        image_data = base64.b64decode(b64_image)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_data)
            tmp_path = f.name
        with open(tmp_path, "rb") as f:
            requests.post(
                f"{MEALIE_URL}/api/recipes/{slug}/images",
                headers={"Authorization": f"Bearer {MEALIE_API_KEY}"},
                files={"image": ("image.jpg", f, "image/jpeg")},
            )
        os.unlink(tmp_path)
    except Exception as e:
        print(f"  ⚠️  Image upload failed: {e}")


def import_recipe(mela_data: dict) -> bool:
    title = mela_data.get("title", "Untitled")

    # Step 1: Create recipe (returns slug)
    resp = requests.post(
        f"{MEALIE_URL}/api/recipes",
        headers=HEADERS,
        json={"name": title},
    )
    if resp.status_code != 201:
        print(f"  ❌ Create failed ({resp.status_code}): {resp.text}")
        return False

    slug = resp.json().strip('"')

    # Step 2: Patch with full data
    payload = parse_mela(mela_data)
    resp = requests.patch(
        f"{MEALIE_URL}/api/recipes/{slug}",
        headers=HEADERS,
        json=payload,
    )
    if resp.status_code != 200:
        print(f"  ❌ Update failed ({resp.status_code}): {resp.text}")
        return False

    # Step 3: Upload first image if present
    images = mela_data.get("images", [])
    if images:
        upload_image(slug, images[0])

    print(f"  ✅ {title} → /r/{slug}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python mela_to_mealie.py recipes.melarecipes")
        sys.exit(1)

    path = sys.argv[1]
    ok = fail = 0

    with zipfile.ZipFile(path, "r") as zf:
        recipe_files = [f for f in zf.namelist() if f.endswith(".melarecipe")]
        print(f"Found {len(recipe_files)} recipes\n")

        for filename in recipe_files:
            print(f"Importing: {filename}")
            with zf.open(filename) as f:
                data = json.load(f)
            if import_recipe(data):
                ok += 1
            else:
                fail += 1

    print(f"\nDone: {ok} imported, {fail} failed")


if __name__ == "__main__":
    main()
