"""
Stalzone Main — слим-база для релиза.
Копирует ТОЛЬКО нужные JSON-предметы в ru/items/.
"""
import json
import os
import shutil

DB_DIR = "stalzone-database"
RECIPES_FILE = "recipes.json"
SLIM_DIR = "stalzone-database-slim"
ITEMS_REL = os.path.join("ru", "items")


def main():
    if not os.path.exists(RECIPES_FILE):
        print(f"[slim] нет {RECIPES_FILE}")
        return

    with open(RECIPES_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    needed = set()
    for r in recipes:
        pid = r.get("productId")
        if pid:
            needed.add(pid)
            if "_" in pid:
                needed.add(pid.rsplit("_", 1)[0])
        for req in r.get("requirements", []):
            iid = req.get("itemId")
            if iid:
                needed.add(iid)
                if "_" in iid:
                    needed.add(iid.rsplit("_", 1)[0])

    print(f"[slim] нужно предметов: {len(needed)}")

    if os.path.exists(SLIM_DIR):
        shutil.rmtree(SLIM_DIR)
    os.makedirs(os.path.join(SLIM_DIR, ITEMS_REL), exist_ok=True)

    src_items = os.path.join(DB_DIR, ITEMS_REL)
    dst_items = os.path.join(SLIM_DIR, ITEMS_REL)

    if not os.path.isdir(src_items):
        print(f"[slim] ОШИБКА: нет папки {src_items}")
        return

    kept = 0
    for dirpath, _, filenames in os.walk(src_items):
        rel = os.path.relpath(dirpath, src_items)
        dst_dir = (os.path.join(dst_items, rel)
                   if rel != "." else dst_items)
        os.makedirs(dst_dir, exist_ok=True)

        for fname in filenames:
            if not fname.endswith(".json"):
                continue
            item_id = fname[:-5]
            if item_id in needed:
                shutil.copy2(os.path.join(dirpath, fname),
                             os.path.join(dst_dir, fname))
                kept += 1

    total = 0
    for dirpath, _, filenames in os.walk(SLIM_DIR):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))

    print(f"[slim] скопировано JSON: {kept}")
    print(f"[slim] размер: {total / 1024 / 1024:.1f} МБ")
    print(f"[slim] готово -> {SLIM_DIR}")


if __name__ == "__main__":
    main()