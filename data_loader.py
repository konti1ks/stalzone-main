"""
Stalzone Main — загрузка всей базы предметов.
Сохраняет id, name, icon (если в JSON), category (для построения URL иконки).
"""
import json
import os
import sys
import time
from pathlib import Path

DB_DIR = "stalzone-database"
RECIPES_FILE = "recipes.json"
REALM = "ru"
ITEMS_SUBPATH = os.path.join(REALM, "items")

# Шаблоны URL для иконок (на случай если URL не указан в JSON)
ICON_CDN_TEMPLATES = (
    "https://raw.githubusercontent.com/EXBO-Studio/stalzone-database/main/ru/icons/{category}/{id}.png",
)


def _user_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    folder = Path(base) / "StalzoneMain"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


CACHE_FILE = _user_dir() / "items_cache.json"
CACHE_VERSION = 22


def _extract_name(name_obj, fallback: str) -> str:
    if isinstance(name_obj, dict):
        lines = name_obj.get("lines", {})
        return lines.get(REALM) or lines.get("en") or fallback
    if isinstance(name_obj, str):
        return name_obj
    return fallback


def _extract_icon(data: dict) -> str:
    """Ищет URL иконки в JSON (может отсутствовать)."""
    for key in ("icon", "image", "imageUrl", "iconUrl"):
        val = data.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
        if isinstance(val, dict):
            for sub in ("url", "href", "src"):
                if isinstance(val.get(sub), str):
                    return val[sub]
    return ""


def load_items(progress_callback=None) -> dict[str, dict]:
    cached = _read_cache()
    if cached is not None:
        print(f"[db] из кэша: {len(cached)} предметов")
        with_cat = sum(1 for m in cached.values() if m.get("category"))
        print(f"[db] с category: {with_cat}")
        if progress_callback:
            progress_callback(1, 1)
        return cached

    root = os.path.join(DB_DIR, ITEMS_SUBPATH)
    if not os.path.isdir(root):
        if not os.path.isdir(DB_DIR):
            raise FileNotFoundError(f"Папка '{DB_DIR}' не найдена.")
        root = DB_DIR

    print(f"[db] сканирую {root} ...")

    files: list[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".json"):
                files.append(os.path.join(dirpath, fname))

    total = len(files)
    print(f"[db] найдено JSON: {total}")
    if total == 0:
        return {}

    items: dict[str, dict] = {}
    t0 = time.time()

    for idx, fpath in enumerate(files):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue
        item_id = data.get("id")
        if not item_id or "name" not in data:
            continue
        if not isinstance(data.get("name"), (dict, str)):
            continue

        items[item_id] = {
            "name": _extract_name(data["name"], item_id),
            "icon": _extract_icon(data),
            "category": data.get("category", ""),
        }

        if idx % 100 == 0 or idx == total - 1:
            if progress_callback:
                progress_callback(idx + 1, total)

    print(f"[db] готово: {len(items)} за {time.time()-t0:.1f}с")
    _write_cache(items)
    return items


def _read_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("version") != CACHE_VERSION:
            return None
        return payload.get("items", {})
    except Exception:
        return None


def _write_cache(items):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"version": CACHE_VERSION, "items": items},
                      f, ensure_ascii=False)
        print("[db] кэш сохранён")
    except Exception as e:
        print(f"[db] кэш: {e}")


def load_hideout_recipes() -> list[dict]:
    if not os.path.exists(RECIPES_FILE):
        return []
    if os.path.getsize(RECIPES_FILE) == 0:
        return []
    try:
        with open(RECIPES_FILE, "r", encoding="utf-8-sig") as f:
            text = f.read().strip()
        if not text:
            return []
        data = json.loads(text)
        if not isinstance(data, list):
            return []
        print(f"[recipes] загружено: {len(data)}")
        return data
    except json.JSONDecodeError as e:
        print(f"[recipes] НЕВАЛИДНЫЙ JSON: {e}")
        return []
    except Exception as e:
        print(f"[recipes] ошибка: {e}")
        return []


def clear_cache():
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()