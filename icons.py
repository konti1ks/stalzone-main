"""Stalzone Main — иконки окна + иконки навыков + менеджер иконок предметов."""
import hashlib
import math
import threading
import urllib.request
from pathlib import Path
from queue import Queue, Empty

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk


# ==========================================================
# ЛОГОТИП / ИКОНКА ОКНА
# ==========================================================
def create_logo_image(size: int = 128) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, size // 20)
    d.rounded_rectangle((pad, pad, size - pad - 1, size - pad - 1),
                        radius=size // 5, fill=(56, 189, 248, 255))
    cx, cy = size // 2, size // 2
    r = int(size * 0.30)
    top = (cx, cy - r)
    right = (cx + int(r * 0.75), cy)
    bottom = (cx, cy + r)
    left = (cx - int(r * 0.75), cy)
    d.polygon([top, right, bottom, left], fill=(10, 14, 20, 255))
    d.line([top, right], fill=(125, 211, 252, 255), width=max(1, size // 60))
    d.line([top, left], fill=(125, 211, 252, 255), width=max(1, size // 60))
    d.line([left, (cx, cy)], fill=(56, 189, 248, 180), width=max(1, size // 80))
    d.line([right, (cx, cy)], fill=(56, 189, 248, 180), width=max(1, size // 80))
    d.line([(cx - r // 3, cy - r // 2), (cx, cy - r + r // 6)],
           fill=(255, 255, 255, 200), width=max(1, size // 80))
    return img


def create_window_icon(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 6
    d.rounded_rectangle((pad, pad, size - pad - 1, size - pad - 1),
                        radius=size // 5,
                        fill=(15, 23, 42, 255),
                        outline=(56, 189, 248, 255),
                        width=max(3, size // 40))
    cx, cy = size // 2, size // 2
    r = int(size * 0.32)
    top = (cx, cy - r)
    right = (cx + int(r * 0.75), cy)
    bottom = (cx, cy + r)
    left = (cx - int(r * 0.75), cy)
    d.polygon([top, right, bottom, left], fill=(56, 189, 248, 255))
    d.polygon([(cx, cy - r + 6), (cx + int(r * 0.55), cy),
               (cx, cy + 2), (cx - int(r * 0.55), cy)],
              fill=(15, 23, 42, 255))
    d.line([(cx, cy - r + 6), (cx, cy + 2)],
           fill=(125, 211, 252, 255), width=max(2, size // 60))
    return img


# ==========================================================
# ИКОНКИ НАВЫКОВ
# ==========================================================
SKILL_ICON_KINDS = {
    "Боеприпасы":          "ammo",
    "Пиротехника":         "pyro",
    "Защитное снаряжение": "shield",
    "Инженерия":           "gear",
    "Кулинария":           "cook",
    "Самогоноварение":     "chem",
    "Медицина":            "med",
    "Сырьё и материалы":   "resource",
    "Химия":               "chem",
    "Биология":            "med",
}

_skill_icon_cache: dict[tuple[str, int], Image.Image] = {}
_SS = 4


def create_skill_icon(kind_or_name: str, size: int = 48) -> Image.Image:
    kind = SKILL_ICON_KINDS.get(kind_or_name, kind_or_name)
    if kind not in ("ammo", "pyro", "shield", "gear",
                    "cook", "chem", "med", "resource"):
        kind = "resource"

    key = (kind, size)
    if key in _skill_icon_cache:
        return _skill_icon_cache[key]

    s = size * _SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ---- палитра (плоский стиль) ----
    bg       = (30, 38, 54, 255)      # тёмно-синий фон
    border   = (56, 90, 140, 255)     # тонкая синеватая обводка
    symbol   = (215, 225, 240, 255)   # светлый символ
    accent   = (56, 189, 248, 255)    # акцентная подсветка

    pad = int(s * 0.05)
    radius = int(s * 0.22)

    # фон — скруглённый квадрат
    d.rounded_rectangle([pad, pad, s - pad - 1, s - pad - 1],
                        radius=radius, fill=bg)
    # тонкая обводка
    d.rounded_rectangle([pad, pad, s - pad - 1, s - pad - 1],
                        radius=radius, outline=border,
                        width=max(1, _SS // 2 + 1))

    cx = s // 2
    cy = s // 2
    r = int(s * 0.28)

    _draw_symbol(d, kind, cx, cy, r, symbol, accent, bg, _SS)

    result = img.resize((size, size), Image.LANCZOS)
    _skill_icon_cache[key] = result
    return result


# ==========================================================
# СИМВОЛЫ
# ==========================================================
def _draw_symbol(d, kind, cx, cy, r, color, accent, bg_dark, ss):
    th = max(1, ss // 2)  # тонкая линия
    if kind == "ammo":
        _sym_ammo(d, cx, cy, r, color, accent, bg_dark, th)
    elif kind == "pyro":
        _sym_pyro(d, cx, cy, r, color, accent, bg_dark, th)
    elif kind == "shield":
        _sym_shield(d, cx, cy, r, color, accent, bg_dark, th)
    elif kind == "gear":
        _sym_gear(d, cx, cy, r, color, accent, bg_dark, th)
    elif kind == "cook":
        _sym_cook(d, cx, cy, r, color, accent, bg_dark, th)
    elif kind == "chem":
        _sym_chem(d, cx, cy, r, color, accent, bg_dark, th)
    elif kind == "med":
        _sym_med(d, cx, cy, r, color, accent, bg_dark, th)
    elif kind == "resource":
        _sym_resource(d, cx, cy, r, color, accent, bg_dark, th)


def _sym_ammo(d, cx, cy, r, color, accent, bg, th):
    """Три патрона."""
    bw = max(4 * th, r // 3)
    bh = int(r * 1.9)
    tip = int(bw * 1.1)
    gap = bw + 3 * th
    top = cy - bh // 2
    for dx in (-gap, 0, gap):
        x0 = cx + dx - bw // 2
        x1 = cx + dx + bw // 2
        y0 = top
        y1 = cy + bh // 2
        # гильза
        d.rounded_rectangle([x0, y0 + tip, x1, y1],
                            radius=bw // 4, fill=color)
        # пуля
        d.polygon([(x0, y0 + tip), (cx + dx, y0), (x1, y0 + tip)],
                  fill=accent)
        # ободок
        d.line([(x0 - th, y1 - 2 * th), (x1 + th, y1 - 2 * th)],
               fill=accent, width=th)


def _sym_pyro(d, cx, cy, r, color, accent, bg, th):
    """Вспышка фейерверка."""
    # центральная звезда
    rays = 8
    for i in range(rays):
        a = math.pi * 2 * i / rays
        ex = cx + int(r * math.cos(a))
        ey = cy + int(r * math.sin(a))
        d.line([(cx, cy), (ex, ey)], fill=color, width=th)
        # точка на конце
        dot = max(2 * th, r // 8)
        d.ellipse([ex - dot, ey - dot, ex + dot, ey + dot], fill=accent)
    # короткие промежуточные лучи
    for i in range(rays):
        a = math.pi * 2 * (i + 0.5) / rays
        ex = cx + int(r * 0.65 * math.cos(a))
        ey = cy + int(r * 0.65 * math.sin(a))
        d.line([(cx, cy), (ex, ey)], fill=accent, width=th)
    # центр
    cr = max(3 * th, r // 5)
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=color)
    ir = max(1 * th, r // 10)
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=bg)


def _sym_shield(d, cx, cy, r, color, accent, bg, th):
    """Геральдический щит с крестом."""
    top_y = cy - r
    half = r
    pts = [
        (cx - half, top_y),
        (cx + half, top_y),
        (cx + half, cy + r // 4),
        (cx, cy + r),
        (cx - half, cy + r // 4),
    ]
    d.polygon(pts, fill=color)
    d.line(pts + [pts[0]], fill=accent, width=th)
    # внутренняя окантовка
    sc = 0.78
    ipts = [(cx + int((p[0] - cx) * sc), cy + int((p[1] - cy) * sc))
            for p in pts]
    d.line(ipts + [ipts[0]], fill=bg, width=th)
    # крест
    aw = max(3 * th, r // 5)
    av = int(r * 0.5)
    d.rectangle([cx - aw // 2, cy - av, cx + aw // 2, cy + int(r * 0.55)],
                fill=bg)
    d.rectangle([cx - int(r * 0.5), cy - aw // 2,
                 cx + int(r * 0.5), cy + aw // 2], fill=bg)


def _sym_gear(d, cx, cy, r, color, accent, bg, th):
    """Шестерёнка."""
    teeth = 8
    out_r = r
    in_r = int(r * 0.76)
    hole = int(r * 0.30)
    pts = []
    for i in range(teeth * 4):
        a = -math.pi / 2 + math.pi * 2 * i / (teeth * 4)
        rr = out_r if i % 4 in (0, 1) else in_r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=color)
    d.line(pts + [pts[0]], fill=accent, width=th)
    d.ellipse([cx - hole, cy - hole, cx + hole, cy + hole], fill=bg)
    d.ellipse([cx - hole, cy - hole, cx + hole, cy + hole],
              outline=accent, width=th)


def _sym_cook(d, cx, cy, r, color, accent, bg, th):
    """Кастрюля с крышкой."""
    bw = int(r * 1.7)
    bt = cy - r // 4
    bb = cy + r * 3 // 4
    x0 = cx - bw // 2
    x1 = cx + bw // 2

    # корпус — трапеция
    d.polygon([
        (x0, bt), (x1, bt),
        (x1 - 3 * th, bb), (x0 + 3 * th, bb),
    ], fill=color)
    d.line([(x0, bt), (x1, bt)], fill=accent, width=th)
    d.line([(x0, bt), (x0 + 3 * th, bb)], fill=accent, width=th)
    d.line([(x1, bt), (x1 - 3 * th, bb)], fill=accent, width=th)

    # ручки
    hw = int(r * 0.30)
    hh = max(2 * th, r // 7)
    hy = bt + 3 * th
    d.rounded_rectangle([x0 - hw, hy, x0, hy + hh],
                        radius=hh // 2, fill=color)
    d.rounded_rectangle([x1, hy, x1 + hw, hy + hh],
                        radius=hh // 2, fill=color)

    # крышка
    lw = bw + 6 * th
    lh = max(4 * th, r // 6)
    ly = bt - lh
    d.rounded_rectangle([cx - lw // 2, ly, cx + lw // 2, ly + lh],
                        radius=lh // 2, fill=color)
    d.line([(cx - lw // 2, ly + lh), (cx + lw // 2, ly + lh)],
           fill=accent, width=th)
    # ручка крышки
    kw = max(4 * th, r // 3)
    kh = max(3 * th, r // 6)
    d.ellipse([cx - kw // 2, ly - kh, cx + kw // 2, ly + 1 * th], fill=accent)


def _sym_chem(d, cx, cy, r, color, accent, bg, th):
    """Бутыль — узкое горлышко, этикетка."""
    bw = int(r * 1.2)
    bt = cy - r // 4
    bb = cy + r
    x0 = cx - bw // 2
    x1 = cx + bw // 2

    nw = max(3 * th, r // 3)
    nt = cy - r
    nb = bt

    # тело
    d.rounded_rectangle([x0, bt, x1, bb - 6 * th],
                        radius=bw // 3, fill=color)
    d.ellipse([x0, bb - 12 * th, x1, bb], fill=color)
    d.line([(x0, bt), (x0, bb - 6 * th)], fill=accent, width=th)
    d.line([(x1, bt), (x1, bb - 6 * th)], fill=accent, width=th)

    # горлышко
    d.rectangle([cx - nw // 2, nt, cx + nw // 2, nb], fill=color)
    d.line([(cx - nw // 2, nt), (cx - nw // 2, nb)], fill=accent, width=th)
    d.line([(cx + nw // 2, nt), (cx + nw // 2, nb)], fill=accent, width=th)

    # пробка
    pw = nw + 4 * th
    ph = max(3 * th, r // 5)
    d.rounded_rectangle([cx - pw // 2, nt - ph, cx + pw // 2, nt],
                        radius=ph // 3, fill=accent)

    # этикетка
    lw = int(bw * 0.8)
    lh = int((bb - bt) * 0.4)
    ly = bt + (bb - bt - lh) // 2
    d.rounded_rectangle([cx - lw // 2, ly, cx + lw // 2, ly + lh],
                        radius=lh // 4, fill=accent)
    d.rounded_rectangle([cx - lw // 2 + 2 * th, ly + 2 * th,
                         cx + lw // 2 - 2 * th, ly + lh - 2 * th],
                        radius=lh // 4, fill=bg)


def _sym_med(d, cx, cy, r, color, accent, bg, th):
    """Аптечка — корпус с ручкой и крестом."""
    bw = int(r * 1.7)
    bh = int(r * 1.2)
    x0 = cx - bw // 2
    x1 = cx + bw // 2
    y0 = cy - bh // 2 + r // 4
    y1 = cy + bh // 2 + r // 4

    # корпус
    d.rounded_rectangle([x0, y0, x1, y1],
                        radius=max(3 * th, r // 8), fill=color)
    d.rounded_rectangle([x0, y0, x1, y1],
                        radius=max(3 * th, r // 8),
                        outline=accent, width=th)

    # ручка сверху
    hw = int(bw * 0.38)
    hh = max(4 * th, r // 4)
    hx0 = cx - hw // 2
    hx1 = cx + hw // 2
    hy0 = y0 - hh
    d.line([(hx0 + 2 * th, y0), (hx0, y0), (hx0, hy0),
            (hx1, hy0), (hx1, y0), (hx1 - 2 * th, y0)],
           fill=accent, width=th)

    # крест
    aw = max(4 * th, bh // 3)
    al = int(bh * 0.42)
    ccx = cx
    ccy = (y0 + y1) // 2
    # тёмная подложка
    d.rectangle([ccx - al - 2 * th, ccy - al - 2 * th,
                 ccx + al + 2 * th, ccy + al + 2 * th], fill=bg)
    # вертикальная
    d.rounded_rectangle([ccx - aw // 2, ccy - al, ccx + aw // 2, ccy + al],
                        radius=aw // 4, fill=accent)
    # горизонтальная
    d.rounded_rectangle([ccx - al, ccy - aw // 2, ccx + al, ccy + aw // 2],
                        radius=aw // 4, fill=accent)


def _sym_resource(d, cx, cy, r, color, accent, bg, th):
    """Слитки в стопке."""
    sw = int(r * 1.05)
    sh = int(r * 0.42)
    sk = int(sh * 0.35)

    def ingot(x0, y0):
        pts = [
            (x0 + sk, y0), (x0 + sw - sk, y0),
            (x0 + sw, y0 + sh), (x0, y0 + sh),
        ]
        d.polygon(pts, fill=color)
        d.line(pts + [pts[0]], fill=accent, width=th)

    yb = cy + int(r * 0.18)
    ingot(cx - sw - 3 * th, yb)
    ingot(cx + 3 * th, yb)
    yt = yb - sh - 3 * th
    ingot(cx - sw // 2, yt)


# ==========================================================
# Менеджер иконок предметов
# ==========================================================
class IconManager:
    def __init__(self, cache_dir, size=(24, 24)):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.size = size
        self._loaded_pil: dict[str, Image.Image] = {}
        self._loaded_ctk: dict[str, ctk.CTkImage] = {}
        self._loaded_tk: dict[str, ImageTk.PhotoImage] = {}
        self._pending: set[str] = set()
        self._queue: Queue = Queue()
        self._results: Queue = Queue()
        self._placeholder_pil = self._make_placeholder()
        self._placeholder_ctk = ctk.CTkImage(
            light_image=self._placeholder_pil,
            dark_image=self._placeholder_pil,
            size=self.size)
        for _ in range(4):
            threading.Thread(target=self._worker, daemon=True).start()

    def _make_placeholder(self) -> Image.Image:
        img = Image.new("RGBA", self.size, (35, 47, 66, 255))
        d = ImageDraw.Draw(img)
        w, h = self.size
        d.ellipse((w // 2 - 3, h // 2 - 3, w // 2 + 3, h // 2 + 3),
                  fill=(56, 189, 248, 140))
        return img

    def get_ctk(self, url: str, name: str) -> ctk.CTkImage:
        pil = self._get_pil(url)
        if pil is None:
            return self._placeholder_ctk
        img = self._loaded_ctk.get(url)
        if img is None:
            img = ctk.CTkImage(light_image=pil, dark_image=pil,
                               size=self.size)
            self._loaded_ctk[url] = img
        return img

    def get_tk(self, url: str, name: str):
        pil = self._get_pil(url)
        if pil is None:
            pil = self._placeholder_pil
        img = self._loaded_tk.get(url)
        if img is None:
            img = ImageTk.PhotoImage(pil)
            self._loaded_tk[url] = img
        return img

    def get_loaded_ctk(self, url: str):
        return self._loaded_ctk.get(url)

    def _get_pil(self, url: str):
        if not url:
            return None
        if url in self._loaded_pil:
            return self._loaded_pil[url]
        fname = hashlib.md5(url.encode()).hexdigest() + ".png"
        path = self.cache_dir / fname
        if path.exists():
            try:
                pil = Image.open(path).convert("RGBA").resize(
                    self.size, Image.LANCZOS)
                self._loaded_pil[url] = pil
                return pil
            except Exception:
                pass
        if url not in self._pending:
            self._pending.add(url)
            self._queue.put((url, path))
        return None

    def poll_ready(self):
        ready = []
        while True:
            try:
                url = self._results.get_nowait()
                self._pending.discard(url)
                fname = hashlib.md5(url.encode()).hexdigest() + ".png"
                path = self.cache_dir / fname
                if path.exists():
                    try:
                        pil = Image.open(path).convert("RGBA").resize(
                            self.size, Image.LANCZOS)
                        self._loaded_pil[url] = pil
                        ready.append(url)
                    except Exception:
                        pass
            except Empty:
                break
        return ready

    def _worker(self):
        while True:
            url, path = self._queue.get()
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "StalzoneMain/26.0"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    if r.status == 200:
                        path.write_bytes(r.read())
            except Exception:
                pass
            self._results.put(url)