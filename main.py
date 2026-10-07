"""
Stalzone Main — калькулятор убежища.
v1.2: тумблер Закупка/Крафт.
"""
import json
import math
import os
import sys
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont
import customtkinter as ctk

from data_loader import load_items, load_hideout_recipes
from models import CraftRecipe, CraftIngredient
from calculator import HideoutCalculator
from icons import (IconManager, create_logo_image, create_window_icon,
                   create_skill_icon, SKILL_ICON_KINDS)

APP_NAME = "Stalzone Main"
APP_VERSION = "1.1"
APP_AUTHOR = "konti1k"

SUPPORT_DISCORD = "https://discord.gg/CaTPHt8DJ"
SUPPORT_TELEGRAM = "https://t.me/kontikqw"

ICON_BASE = ("https://raw.githubusercontent.com/EXBO-Studio/"
             "stalzone-database/main/ru/icons")

ALL_SKILLS = [
    "Боеприпасы",
    "Пиротехника",
    "Защитное снаряжение",
    "Инженерия",
    "Кулинария",
    "Самогоноварение",
    "Медицина",
    "Сырьё и материалы",
]

SKILL_MIN = 1
SKILL_MAX = 5
SKILL_DEFAULT = 1

ITEMS_SORT_CYCLE = [
    ("Имя ↑", "name_asc"),
    ("Имя ↓", "name_desc"),
    ("Цена ↑", "price_asc"),
    ("Цена ↓", "price_desc"),
]
RECIPES_SORT_CYCLE = [
    ("Имя ↑", "name_asc"),
    ("Имя ↓", "name_desc"),
    ("✓ сначала", "avail_first"),
    ("🔒 сначала", "locked_first"),
]

AUCTION_FEE = 0.05


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_user_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    folder = Path(base) / "StalzoneMain"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


APP_DIR = app_dir()
USER_DIR = get_user_data_dir()
PRICES_FILE = USER_DIR / "prices.json"
SALE_PRICES_FILE = USER_DIR / "sale_prices.json"
SKILLS_FILE = USER_DIR / "skills.json"
NOTES_FILE = USER_DIR / "notes.txt"
ICONS_CACHE = USER_DIR / "icons"
APP_ICO = APP_DIR / "app.ico"

C_BG        = "#070a10"
C_SIDEBAR   = "#0b0f18"
C_SURFACE   = "#0e131d"
C_SURFACE_2 = "#1a2231"
C_SURFACE_3 = "#232e40"
C_SURFACE_4 = "#2c3a52"
C_BORDER    = "#2b3a53"
C_BORDER_2  = "#1e2a3d"
C_TEXT      = "#eaf1fa"
C_TEXT_DIM  = "#8b98aa"
C_TEXT_MUT  = "#59657a"
C_ACCENT    = "#38bdf8"
C_ACCENT_H  = "#7dd3fc"
C_ACCENT_D  = "#0c4a6e"
C_ACCENT_P  = "#a78bfa"
C_OK        = "#4ade80"
C_BAD       = "#f87171"
C_WARN      = "#fbbf24"
C_HOVER     = "#2a3a52"

C_MENU_BG       = "#1e2836"
C_MENU_BORDER   = "#3b4a63"
C_MENU_HOVER    = "#2e3e56"
C_MENU_TEXT     = "#f0f4fa"

ctk.set_appearance_mode("dark")

F_DISPLAY = "Segoe UI"
F_MONO = "Consolas"


def _lerp_color(c1, c2, t):
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def pick_fonts():
    global F_DISPLAY, F_MONO
    try:
        available = set(tkfont.families())
    except Exception:
        return
    for f in ("Bahnschrift", "Bahnschrift SemiBold",
              "Segoe UI Variable Display", "Segoe UI"):
        if f in available:
            F_DISPLAY = f
            break
    for f in ("Cascadia Code", "Cascadia Mono",
              "JetBrains Mono", "Consolas", "Courier New"):
        if f in available:
            F_MONO = f
            break
    print(f"[fonts] {F_DISPLAY} / {F_MONO}")


def lock_text_selection(textbox: ctk.CTkTextbox):
    try:
        inner = textbox._textbox
        for ev in ("<Button-1>", "<B1-Motion>",
                   "<Double-Button-1>", "<Triple-Button-1>",
                   "<Control-a>", "<Control-A>",
                   "<Control-c>", "<Control-C>",
                   "<Control-x>", "<Control-X>",
                   "<Control-v>", "<Control-V>",
                   "<Control-Insert>", "<Shift-Insert>"):
            inner.bind(ev, lambda e: "break")
        inner.configure(cursor="arrow")
        inner.configure(state="disabled")
        textbox.configure(cursor="arrow")
    except Exception as e:
        print(f"[lock_text] {e}")


class ModernDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, width: int = 380, height: int = 260):
        super().__init__(parent)
        self._parent = parent
        self._closed = False

        self.overrideredirect(True)
        self.configure(fg_color=C_BORDER)

        outer = ctk.CTkFrame(self, fg_color=C_BG,
                             corner_radius=12,
                             border_width=1, border_color=C_BORDER)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(outer, fg_color=C_BG, corner_radius=12,
                              height=38)
        header.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=title,
                     text_color=C_TEXT,
                     font=(F_DISPLAY, 12, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="w",
                                      padx=(12, 0), pady=8)

        ctk.CTkButton(
            header, text="✕", command=self._on_cancel,
            width=24, height=24,
            fg_color="transparent", hover_color=C_SURFACE_3,
            text_color=C_TEXT_DIM, corner_radius=6,
            font=(F_DISPLAY, 11)
        ).grid(row=0, column=1, sticky="e", padx=(0, 6), pady=8)

        sep = tk.Frame(outer, bg=C_BORDER, height=1)
        sep.grid(row=0, column=0, sticky="sew", pady=(37, 0))

        self.body = ctk.CTkFrame(outer, fg_color=C_BG, corner_radius=0)
        self.body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 4))

        self.footer = ctk.CTkFrame(outer, fg_color=C_BG, corner_radius=12)
        self.footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))

        self.geometry(f"{width}x{height}")
        self._center_on_parent(width, height)

        self.transient(parent)
        self.lift()
        self.after(30, self._activate)
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _center_on_parent(self, w, h):
        try:
            self._parent.update_idletasks()
            px = self._parent.winfo_rootx()
            py = self._parent.winfo_rooty()
            pw = self._parent.winfo_width()
            ph = self._parent.winfo_height()
            if pw <= 1 or ph <= 1:
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = (sw - w) // 2
                y = (sh - h) // 2
            else:
                x = px + (pw - w) // 2
                y = py + (ph - h) // 2
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _activate(self):
        if self._closed:
            return
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _on_cancel(self):
        self._close()

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def show(self):
        self.wait_window()
        try:
            self._parent.focus_force()
        except Exception:
            pass
        return None


class ModernContextMenu(tk.Toplevel):
    KEY_COLOR = "#ff01fe"

    def __init__(self, parent, actions, x, y, on_close=None):
        super().__init__(parent)
        self._closed = False
        self._on_close_cb = on_close
        self._root_bind_id = None
        self._menu_root = parent.winfo_toplevel()

        self.overrideredirect(True)
        try:
            self.wm_attributes("-topmost", True)
        except Exception:
            pass

        self._transparent_ok = False
        try:
            self.wm_attributes("-transparentcolor", self.KEY_COLOR)
            self._transparent_ok = True
        except Exception:
            pass

        if self._transparent_ok:
            self.configure(bg=self.KEY_COLOR)
        else:
            self.configure(bg=C_MENU_BG)

        self.geometry(f"10x10+{x}+{y}")
        card_bg_color = self.KEY_COLOR if self._transparent_ok else C_MENU_BG

        self.card = ctk.CTkFrame(
            self, fg_color=C_MENU_BG,
            corner_radius=12,
            border_width=1, border_color=C_MENU_BORDER,
            bg_color=card_bg_color)
        self.card.pack(fill="both", expand=True)

        n = len(actions)
        for i, (label, cb) in enumerate(actions):
            pady = (6 if i == 0 else 2, 6 if i == n - 1 else 2)
            ctk.CTkButton(
                self.card, text=label, anchor="w",
                command=lambda c=cb: self._pick(c),
                fg_color="transparent",
                hover_color=C_MENU_HOVER,
                text_color=C_MENU_TEXT,
                corner_radius=8,
                height=34,
                font=(F_DISPLAY, 12, "bold")
            ).pack(fill="x", padx=7, pady=pady)

        self.update_idletasks()
        w = max(190, self.winfo_reqwidth())
        h = self.winfo_reqheight()

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(4, min(x, sw - w - 4))
        y = max(4, min(y, sh - h - 4))
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.bind("<Escape>", lambda e: self.close())
        self.after(20, self._activate)

    def _activate(self):
        if self._closed:
            return
        try:
            self.focus_force()
        except Exception:
            pass
        try:
            self._root_bind_id = self._menu_root.bind(
                "<Button-1>", self._on_global_click, add="+")
        except Exception:
            self._root_bind_id = None

    def _on_global_click(self, event):
        if self._closed:
            return
        try:
            w = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            w = None
        node = w
        while node is not None:
            if node is self:
                return
            try:
                node = node.master
            except Exception:
                break
        self.close()

    def _pick(self, cb):
        self.close()
        try:
            self.after(20, cb)
        except Exception:
            pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._root_bind_id is not None:
            try:
                self._menu_root.unbind("<Button-1>", self._root_bind_id)
            except Exception:
                pass
            self._root_bind_id = None
        if self._on_close_cb:
            try:
                self._on_close_cb(self)
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass


class CanvasList(tk.Frame):
    def __init__(self, parent, row_height=46, kind="item"):
        super().__init__(parent, bg=C_SURFACE, bd=0, highlightthickness=0)
        self.row_height = row_height
        self.kind = kind

        self.items = []
        self.item_data = []
        self.item_rects: dict[int, list[int]] = {}
        self._row_fix: dict[int, dict] = {}
        self._prep_fn = None

        self._hover_idx = -1
        self._selected_idx = -1
        self._on_click_cb = None
        self._on_right_cb = None
        self._empty_msg = ""

        self._drawn_width = -1
        self._rebuild_pending = False
        self._rebuild_attempts = 0

        self._resize_timer = None
        self._resize_pending_width = -1

        self.canvas = tk.Canvas(self, bg=C_SURFACE,
                                highlightthickness=0, bd=0)
        self.scrollbar = ctk.CTkScrollbar(
            self, command=self.canvas.yview, width=14,
            button_color=C_SURFACE_3,
            button_hover_color=C_ACCENT_D,
            fg_color=C_SURFACE)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Map>", self._on_map)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_rclick)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel)
        self.canvas.bind("<Button-5>", self._on_wheel)

    def set_data(self, items, on_click, on_right_click,
                 empty_message="", prep=None):
        self.items = items or []
        self._on_click_cb = on_click
        self._on_right_cb = on_right_click
        self._empty_msg = empty_message
        self._prep_fn = prep
        self._selected_idx = -1
        self._rebuild_pending = True
        self._rebuild_attempts = 0
        self.after(15, self._try_rebuild)

    def redraw(self):
        self._rebuild_pending = True
        self._rebuild_attempts = 0
        self.after(15, self._try_rebuild)

    def smart_redraw(self):
        try:
            self.update_idletasks()
        except Exception:
            pass
        w = self.canvas.winfo_width()
        if w <= 10:
            return
        if abs(w - self._drawn_width) <= 4:
            return
        if self._row_fix:
            self._quick_resize(w)
        else:
            self._rebuild_pending = True
            self._rebuild_attempts = 0
            self.after(15, self._try_rebuild)

    def set_selected(self, predicate):
        old = self._selected_idx
        self._selected_idx = -1
        for idx, item in enumerate(self.items):
            if predicate(item):
                self._selected_idx = idx
                break
        if old >= 0:
            self._repaint_row_bg(old)
        if self._selected_idx >= 0:
            self._repaint_row_bg(self._selected_idx)

    def update_icon(self, idx: int, photo):
        if idx not in self.item_rects:
            return
        if idx >= len(self.item_data):
            return
        self.item_data[idx]["icon_photo"] = photo
        self._redraw_row(idx)

    def update_value(self, idx: int, value: str, color: str):
        if idx not in self._row_fix:
            return
        d = self._row_fix[idx]
        vid = d.get("value")
        if vid is None:
            return
        try:
            self.canvas.itemconfigure(vid, text=value, fill=color)
        except Exception:
            pass
        if idx < len(self.item_data):
            self.item_data[idx]["value"] = value
            self.item_data[idx]["value_color"] = color

    def _on_map(self, _e):
        if self._drawn_width > 10 and self._row_fix:
            try:
                self.update_idletasks()
            except Exception:
                pass
            w = self.canvas.winfo_width()
            if w > 10 and abs(w - self._drawn_width) > 4:
                self._quick_resize(w)
            return
        self._rebuild_pending = True
        self._rebuild_attempts = 0
        self.after(15, self._try_rebuild)

    def _best_width(self):
        w = self.canvas.winfo_width()
        if w > 10:
            return w
        node = self.canvas
        for _ in range(6):
            try:
                node = node.master
            except Exception:
                break
            if node is None:
                break
            try:
                pw = node.winfo_width()
            except Exception:
                pw = 0
            if pw > 10:
                return pw - 20
        return 800

    def _try_rebuild(self):
        if not self._rebuild_pending:
            return
        try:
            self.update_idletasks()
        except Exception:
            pass
        w = self.canvas.winfo_width()
        if w <= 10:
            self._rebuild_attempts += 1
            if self._rebuild_attempts < 40:
                self.after(20, self._try_rebuild)
                return
        self._rebuild_pending = False
        self._rebuild()

    def _on_resize(self, event):
        if event.width <= 10:
            return
        if abs(event.width - self._drawn_width) <= 4:
            return
        if self._rebuild_pending:
            return
        self._resize_pending_width = event.width
        if self._resize_timer is not None:
            try:
                self.after_cancel(self._resize_timer)
            except Exception:
                pass
        self._resize_timer = self.after(70, self._flush_resize)

    def _flush_resize(self):
        self._resize_timer = None
        w = self._resize_pending_width
        self._resize_pending_width = -1
        if w <= 10:
            return
        if abs(w - self._drawn_width) <= 4:
            return
        self._quick_resize(w)

    def _quick_resize(self, w):
        if not self._row_fix:
            return
        self._drawn_width = w
        canvas = self.canvas
        for idx, d in self._row_fix.items():
            y0 = d["y0"]
            y1 = d["y1"]
            cy = (y0 + y1) / 2
            try:
                canvas.coords(d["bg"], 4, y0, w - 4, y1)
                canvas.coords(d["bar"], 4, y0, 6, y1)
                if d.get("value") is not None:
                    canvas.coords(d["value"], w - 16, cy)
                if d.get("count") is not None:
                    canvas.coords(d["count"], w - 16, cy)
                if d.get("lock") is not None:
                    canvas.coords(d["lock"], w - 80, cy)
            except Exception:
                pass

    def _rebuild(self):
        self.canvas.delete("all")
        self.item_rects.clear()
        self._row_fix.clear()
        self.item_data.clear()
        self._hover_idx = -1

        w = self._best_width()
        self._drawn_width = w

        if not self.items:
            if self._empty_msg:
                self.canvas.create_text(
                    w // 2, 70, text="◌",
                    fill=C_TEXT_MUT, font=(F_DISPLAY, 44), tags="empty_icon")
                self.canvas.create_text(
                    w // 2, 125, text=self._empty_msg,
                    fill=C_TEXT_MUT, font=(F_DISPLAY, 12),
                    width=w - 60, justify="center", tags="empty_msg")
            self.canvas.configure(scrollregion=(0, 0, 1, 1))
            return

        total_h = len(self.items) * self.row_height
        self.canvas.configure(scrollregion=(0, 0, 1, max(total_h, 1)))

        prepared = []
        for item in self.items:
            data = self._prep_fn(item) if self._prep_fn else {}
            prepared.append(data)
        self.item_data = prepared

        for i, data in enumerate(prepared):
            self._draw_row(i, data, w)

    def _row_colors(self, idx, data):
        if idx == self._selected_idx:
            bg = C_SURFACE_3
        else:
            bg = C_SURFACE_2
        if self.kind == "recipe":
            bar = data.get("bar_color") or C_ACCENT_D
        else:
            bar = C_ACCENT_D
        return bg, bar

    def _draw_row(self, idx, data, w):
        y0 = idx * self.row_height + 2
        y1 = y0 + self.row_height - 4
        cy = (y0 + y1) / 2
        ids = []

        bg_color, bar_color = self._row_colors(idx, data)

        bg = self.canvas.create_rectangle(
            4, y0, w - 4, y1,
            fill=bg_color, outline=C_BORDER_2, width=1, tags="row_bg")
        ids.append(bg)

        bar = self.canvas.create_rectangle(
            4, y0, 6, y1,
            fill=bar_color, outline="", tags="row_accent")
        ids.append(bar)

        fix = {"bg": bg, "bar": bar,
               "y0": y0, "y1": y1,
               "value": None, "count": None, "lock": None}

        if self.kind == "item":
            icon_x = 16
            photo = data.get("icon_photo")
            if photo is not None:
                ic = self.canvas.create_image(
                    icon_x + 11, cy, image=photo,
                    anchor="center", tags="row_icon")
            else:
                ic = self.canvas.create_rectangle(
                    icon_x, cy - 11, icon_x + 22, cy + 11,
                    fill=C_SURFACE_4, outline="", tags="row_icon")
            ids.append(ic)

            name_x = icon_x + 22 + 10
            nt = self.canvas.create_text(
                name_x, cy, text=data.get("name", ""),
                fill=data.get("name_color", C_TEXT),
                font=(F_DISPLAY, 12), anchor="w", tags="row_text_name")
            ids.append(nt)

            pt = self.canvas.create_text(
                w - 16, cy, text=data.get("value", "—"),
                fill=data.get("value_color", C_TEXT_MUT),
                font=(F_MONO, 12, "bold"), anchor="e", tags="row_text_value")
            ids.append(pt)
            fix["value"] = pt

        else:
            chip_text = data.get("chip", "")
            chip_x = 18
            chip = self.canvas.create_text(
                chip_x, cy, text=chip_text,
                fill=data.get("chip_color", C_ACCENT),
                font=(F_DISPLAY, 10, "bold"), anchor="w",
                tags="row_text_chip")
            ids.append(chip)

            bbox = self.canvas.bbox(chip)
            if bbox:
                chip_bg = self.canvas.create_rectangle(
                    bbox[0] - 7, bbox[1] - 3, bbox[2] + 7, bbox[3] + 3,
                    fill=data.get("chip_bg", C_SURFACE_3),
                    outline="", tags="row_bg_chip")
                self.canvas.tag_lower(chip_bg, chip)
                self.canvas.tag_lower(chip_bg, bar)
                ids.append(chip_bg)
                name_x = bbox[2] + 16
            else:
                name_x = chip_x + 130

            nt = self.canvas.create_text(
                name_x, cy, text=data.get("name", ""),
                fill=data.get("name_color", C_TEXT),
                font=(F_DISPLAY, 12), anchor="w", tags="row_text_name")
            ids.append(nt)

            ct = self.canvas.create_text(
                w - 16, cy, text=data.get("count_str", ""),
                fill=data.get("count_color", C_ACCENT),
                font=(F_MONO, 12, "bold"), anchor="e",
                tags="row_text_count")
            ids.append(ct)
            fix["count"] = ct

            reason = data.get("reason", "")
            if reason:
                lt = self.canvas.create_text(
                    w - 80, cy, text="🔒 " + reason,
                    fill=C_BAD, font=(F_DISPLAY, 10), anchor="e",
                    tags="row_text_lock")
                ids.append(lt)
                fix["lock"] = lt

        self.item_rects[idx] = ids
        self._row_fix[idx] = fix

    def _repaint_row_bg(self, idx):
        if idx not in self.item_rects or idx not in self._row_fix:
            return
        data = self.item_data[idx] if idx < len(self.item_data) else {}
        bg_color, _ = self._row_colors(idx, data)
        try:
            self.canvas.itemconfigure(self._row_fix[idx]["bg"], fill=bg_color)
        except Exception:
            pass

    def _idx_at_y(self, y):
        cy = self.canvas.canvasy(y)
        if cy < 0:
            return -1
        idx = int(cy // self.row_height)
        if 0 <= idx < len(self.items):
            return idx
        return -1

    def _on_motion(self, event):
        idx = self._idx_at_y(event.y)
        if idx == self._hover_idx:
            return
        if self._hover_idx >= 0 and self._hover_idx in self._row_fix:
            d = self._row_fix[self._hover_idx]
            try:
                if self._hover_idx == self._selected_idx:
                    self.canvas.itemconfigure(d["bg"], fill=C_SURFACE_3)
                else:
                    self.canvas.itemconfigure(d["bg"], fill=C_SURFACE_2)
                self.canvas.itemconfigure(
                    d["bar"],
                    fill=self.item_data[self._hover_idx].get(
                        "bar_color", C_ACCENT_D)
                    if self.kind == "recipe" else C_ACCENT_D)
            except Exception:
                pass
        self._hover_idx = idx
        if idx >= 0 and idx in self._row_fix:
            d = self._row_fix[idx]
            try:
                self.canvas.itemconfigure(d["bg"], fill=C_HOVER)
                self.canvas.itemconfigure(d["bar"], fill=C_ACCENT)
            except Exception:
                pass

    def _on_leave(self, _e):
        if self._hover_idx >= 0 and self._hover_idx in self._row_fix:
            d = self._row_fix[self._hover_idx]
            try:
                if self._hover_idx == self._selected_idx:
                    self.canvas.itemconfigure(d["bg"], fill=C_SURFACE_3)
                else:
                    self.canvas.itemconfigure(d["bg"], fill=C_SURFACE_2)
                self.canvas.itemconfigure(
                    d["bar"],
                    fill=self.item_data[self._hover_idx].get(
                        "bar_color", C_ACCENT_D)
                    if self.kind == "recipe" else C_ACCENT_D)
            except Exception:
                pass
        self._hover_idx = -1

    def _on_click(self, event):
        idx = self._idx_at_y(event.y)
        if idx >= 0 and self._on_click_cb:
            self._on_click_cb(self.items[idx])

    def _on_rclick(self, event):
        idx = self._idx_at_y(event.y)
        if idx >= 0 and self._on_right_cb:
            self._on_right_cb(event, self.items[idx])

    def _on_wheel(self, event):
        if getattr(event, "num", None) == 4:
            step = -3
        elif getattr(event, "num", None) == 5:
            step = 3
        else:
            step = -int(event.delta / 120) * 3 or (
                -3 if event.delta > 0 else 3)
        self.canvas.yview_scroll(step, "units")

    def _redraw_row(self, idx):
        if idx not in self.item_rects:
            return
        for iid in self.item_rects[idx]:
            try:
                self.canvas.delete(iid)
            except Exception:
                pass
        w = self._drawn_width if self._drawn_width > 10 else self._best_width()
        self._draw_row(idx, self.item_data[idx], w)


class SidebarTab(ctk.CTkFrame):
    def __init__(self, parent, key, label, symbol, on_click):
        super().__init__(parent, fg_color="transparent",
                         corner_radius=8, height=42)
        self.pack_propagate(False)
        self.key = key
        self.on_click = on_click

        self.accent_bar = ctk.CTkFrame(self, fg_color="transparent",
                                       width=3, corner_radius=2)
        self.accent_bar.pack(side="left", fill="y", pady=8)
        self.accent_bar.pack_propagate(False)

        self.symbol_label = ctk.CTkLabel(
            self, text=symbol, width=24, text_color=C_TEXT_MUT,
            font=(F_DISPLAY, 17))
        self.symbol_label.pack(side="left", padx=(8, 4))

        self.text_label = ctk.CTkLabel(
            self, text=label, anchor="w", text_color=C_TEXT_DIM,
            font=(F_DISPLAY, 13))
        self.text_label.pack(side="left", fill="x", expand=True)

        for w in (self, self.symbol_label, self.text_label, self.accent_bar):
            try:
                w.bind("<Button-1>", lambda e: self.on_click(self.key), add="+")
                w.configure(cursor="hand2")
            except Exception:
                pass

    def set_active(self, active):
        if active:
            self.configure(fg_color=C_SURFACE_2)
            self.accent_bar.configure(fg_color=C_ACCENT)
            self.symbol_label.configure(text_color=C_ACCENT)
            self.text_label.configure(text_color=C_TEXT)
        else:
            self.configure(fg_color="transparent")
            self.accent_bar.configure(fg_color="transparent")
            self.symbol_label.configure(text_color=C_TEXT_MUT)
            self.text_label.configure(text_color=C_TEXT_DIM)


class SkillStepper(ctk.CTkFrame):
    def __init__(self, parent, skill, value, on_change, min_val, max_val):
        super().__init__(parent, fg_color=C_BG,
                         corner_radius=8,
                         border_width=1, border_color=C_BORDER,
                         height=34)
        self.pack_propagate(False)
        self.configure(width=116)

        self.skill = skill
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.on_change = on_change

        self.minus_btn = ctk.CTkButton(
            self, text="−", command=lambda: self._change(-1),
            width=32, height=32,
            fg_color="transparent", hover_color=C_SURFACE_3,
            text_color=C_TEXT, corner_radius=6,
            font=(F_DISPLAY, 16, "bold"))
        self.minus_btn.pack(side="left", padx=(1, 0), pady=1)

        self.value_label = ctk.CTkLabel(
            self, text=str(value), text_color=C_ACCENT,
            font=(F_MONO, 14, "bold"), width=44)
        self.value_label.pack(side="left", fill="both", expand=True)

        self.plus_btn = ctk.CTkButton(
            self, text="+", command=lambda: self._change(1),
            width=32, height=32,
            fg_color="transparent", hover_color=C_SURFACE_3,
            text_color=C_ACCENT, corner_radius=6,
            font=(F_DISPLAY, 16, "bold"))
        self.plus_btn.pack(side="right", padx=(0, 1), pady=1)

        self.update_state()

    def _change(self, delta):
        new_val = self.value + delta
        new_val = max(self.min_val, min(self.max_val, new_val))
        if new_val == self.value:
            return
        self.value = new_val
        self.value_label.configure(text=str(new_val))
        self.update_state()
        if self.on_change:
            self.on_change(self.skill, new_val)

    def update_state(self):
        self.minus_btn.configure(
            state="disabled" if self.value <= self.min_val else "normal",
            text_color=C_TEXT_MUT if self.value <= self.min_val else C_TEXT)
        self.plus_btn.configure(
            state="disabled" if self.value >= self.max_val else "normal",
            text_color=C_TEXT_MUT if self.value >= self.max_val else C_ACCENT)


class FloatingWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, width, height, resizable=False):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.configure(fg_color=C_BG)
        self.resizable(resizable, resizable)
        self.transient(parent)

        self._closed = False
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        try:
            parent.update_idletasks()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - width) // 2
            y = py + (ph - height) // 2
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

        self.after(80, self._lift)

    def _lift(self):
        try:
            self.lift()
        except Exception:
            pass

    def _on_close(self):
        self._closed = True
        try:
            self.destroy()
        except Exception:
            pass


class NotesWindow(FloatingWindow):
    def __init__(self, parent):
        super().__init__(parent, "Заметки", 520, 440, resizable=True)

        wrap = ctk.CTkFrame(self, fg_color=C_BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)

        head = ctk.CTkFrame(wrap, fg_color="transparent")
        head.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(head, text="Личные заметки",
                     text_color=C_TEXT, font=(F_DISPLAY, 13, "bold"),
                     anchor="w").pack(side="left")
        self.status_label = ctk.CTkLabel(
            head, text="", text_color=C_TEXT_MUT,
            font=(F_DISPLAY, 10), anchor="e")
        self.status_label.pack(side="right")

        self.textbox = ctk.CTkTextbox(
            wrap, fg_color=C_SURFACE_2, corner_radius=10,
            text_color=C_TEXT, border_width=1, border_color=C_BORDER,
            font=(F_MONO, 12),
            scrollbar_button_color=C_SURFACE_3,
            scrollbar_button_hover_color=C_ACCENT_D)
        self.textbox.pack(fill="both", expand=True)
        self.textbox.bind("<KeyRelease>", self._on_change)

        try:
            if NOTES_FILE.exists():
                self.textbox.insert("1.0",
                                    NOTES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

        foot = ctk.CTkFrame(wrap, fg_color="transparent")
        foot.pack(fill="x", pady=(8, 0))

        ctk.CTkLabel(foot, text=f"автосохранение  ·  {NOTES_FILE.name}",
                     text_color=C_TEXT_MUT, font=(F_DISPLAY, 10),
                     anchor="w").pack(side="left")

        ctk.CTkButton(foot, text="Очистить", command=self._clear,
                      fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
                      text_color=C_BAD, corner_radius=8, height=32,
                      border_width=1, border_color=C_BORDER,
                      font=(F_DISPLAY, 11), width=110
                      ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(foot, text="Сохранить", command=self._save,
                      fg_color=C_ACCENT, hover_color=C_ACCENT_H,
                      text_color="#0a0e14", corner_radius=8, height=32,
                      font=(F_DISPLAY, 11, "bold"), width=130
                      ).pack(side="right")

        self._save_timer = None

    def _on_change(self, _e=None):
        if self._save_timer is not None:
            try:
                self.after_cancel(self._save_timer)
            except Exception:
                pass
        self._save_timer = self.after(600, self._save)

    def _save(self):
        self._save_timer = None
        try:
            content = self.textbox.get("1.0", "end-1c")
            NOTES_FILE.write_text(content, encoding="utf-8")
            self.status_label.configure(text="✓ сохранено")
            self.after(1500, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.status_label.configure(text=f"ошибка: {e}")

    def _clear(self):
        self.textbox.delete("1.0", "end")
        self._save()


class CalculatorWindow(FloatingWindow):
    def __init__(self, parent):
        super().__init__(parent, "Калькулятор", 300, 420, resizable=False)

        self._expr = tk.StringVar(value="")
        self._result = tk.StringVar(value="0")

        outer = ctk.CTkFrame(self, fg_color=C_BG)
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        display = ctk.CTkFrame(outer, fg_color=C_SURFACE_2,
                               corner_radius=10,
                               border_width=1, border_color=C_BORDER,
                               height=80)
        display.pack(fill="x", pady=(0, 10))
        display.pack_propagate(False)

        ctk.CTkLabel(display, textvariable=self._expr,
                     text_color=C_TEXT_MUT, font=(F_MONO, 11),
                     anchor="e").pack(fill="x", padx=14, pady=(12, 0))

        ctk.CTkLabel(display, textvariable=self._result,
                     text_color=C_TEXT, font=(F_MONO, 22, "bold"),
                     anchor="e").pack(fill="x", padx=14, pady=(0, 12))

        grid = ctk.CTkFrame(outer, fg_color="transparent")
        grid.pack(fill="both", expand=True)

        for c in range(4):
            grid.grid_columnconfigure(c, weight=1, uniform="calc")
        for r in range(5):
            grid.grid_rowconfigure(r, weight=1, uniform="calc")

        layout = [
            ("C",  "±", "%",  "÷"),
            ("7",  "8", "9",  "×"),
            ("4",  "5", "6",  "−"),
            ("1",  "2", "3",  "+"),
            ("0",  ".", "⌫",  "="),
        ]

        for r, row in enumerate(layout):
            for c, label in enumerate(row):
                if label == "=":
                    fg, hov, txt = C_ACCENT, C_ACCENT_H, "#0a0e14"
                elif label in ("C", "⌫"):
                    fg, hov, txt = "transparent", C_SURFACE_3, C_BAD
                elif label in ("÷", "×", "−", "+"):
                    fg, hov, txt = "transparent", C_SURFACE_3, C_ACCENT
                elif label in ("%", "±"):
                    fg, hov, txt = "transparent", C_SURFACE_3, C_TEXT_DIM
                else:
                    fg, hov, txt = "transparent", C_SURFACE_3, C_TEXT
                ctk.CTkButton(
                    grid, text=label,
                    command=lambda l=label: self._press(l),
                    fg_color=fg, hover_color=hov,
                    text_color=txt, corner_radius=8,
                    font=(F_DISPLAY, 16),
                    border_width=0,
                    width=1, height=1
                ).grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

        self.bind("<Key>", self._on_key)

    def _press(self, label):
        e = self._expr.get()
        if label == "C":
            self._expr.set("")
            self._result.set("0")
            return
        if label == "⌫":
            self._expr.set(e[:-1])
            self._compute()
            return
        if label == "=":
            self._compute(final=True)
            return
        if label == "±":
            if e.startswith("-"):
                self._expr.set(e[1:])
            elif e:
                self._expr.set("-" + e)
            self._compute()
            return
        if label == "%":
            if e:
                self._expr.set(e + "/100")
                self._compute()
            return
        self._expr.set(e + label)
        self._compute()

    def _compute(self, final=False):
        e = self._expr.get()
        s = (e.replace("÷", "/").replace("×", "*")
             .replace("−", "-").replace(",", "."))
        if not s:
            self._result.set("0")
            return
        try:
            val = eval(s, {"__builtins__": {}}, {})
            if isinstance(val, (int, float)):
                if abs(val - round(val)) < 1e-9:
                    out = str(int(round(val)))
                else:
                    out = f"{val:.6g}"
                self._result.set(out)
                if final:
                    self._expr.set(out)
            else:
                self._result.set("0")
        except Exception:
            if final:
                self._result.set("ошибка")

    def _on_key(self, event):
        k = event.char
        if k.isdigit() or k in "+-*/.":
            self._press(k)
        elif k == ",":
            self._press(".")
        elif k == "\r":
            self._compute(final=True)
        elif event.keysym == "BackSpace":
            self._press("⌫")
        elif event.keysym == "Escape":
            self._press("C")


class InfoWindow(FloatingWindow):
    def __init__(self, parent):
        super().__init__(parent, "Информация", 640, 560, resizable=True)

        outer = ctk.CTkFrame(self, fg_color=C_BG)
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        tb = ctk.CTkTextbox(
            outer, fg_color=C_SURFACE_2, corner_radius=10,
            text_color=C_TEXT, border_width=1, border_color=C_BORDER,
            font=(F_MONO, 12),
            scrollbar_button_color=C_SURFACE_3,
            scrollbar_button_hover_color=C_ACCENT_D)
        tb.pack(fill="both", expand=True)

        inner = tb._textbox
        inner.tag_configure("h1", foreground=C_ACCENT,
                            font=(F_DISPLAY, 18, "bold"),
                            spacing1=4, spacing3=8)
        inner.tag_configure("h2", foreground=C_ACCENT_P,
                            font=(F_DISPLAY, 13, "bold"),
                            spacing1=10, spacing3=4)
        inner.tag_configure("body", foreground=C_TEXT_DIM,
                            font=(F_DISPLAY, 11),
                            spacing3=3)
        inner.tag_configure("bullet", foreground=C_TEXT,
                            font=(F_DISPLAY, 11),
                            lmargin1=14, lmargin2=28)
        inner.tag_configure("author", foreground=C_TEXT,
                            font=(F_DISPLAY, 12, "bold"),
                            spacing1=8)
        inner.tag_configure("author_val", foreground=C_ACCENT,
                            font=(F_MONO, 12, "bold"))
        inner.tag_configure("sep", foreground=C_BORDER,
                            font=(F_DISPLAY, 6))

        dm_palette = [
            "#4a2e3e", "#3a2e4a", "#2e3a4a", "#4a3e2e", "#2e4a3a",
        ]

        tb.insert("end", f"{APP_NAME}\n", "h1")
        tb.insert("end", f"версия {APP_VERSION}\n", "body")
        tb.insert("end", "Калькулятор для расчёта крафта в убежище.\n", "body")

        tb.insert("end", "Возможности\n", "h2")
        for line in [
            "Себестоимость любого рецепта из базы данных",
            "Учёт уровней навыков — недоступные рецепты блокируются",
            "Тумблер «Закупка | Крафт» — считает по ценам или по крафту",
            "Прибыль при продаже с рук и через аукцион",
            "Автосохранение цен, навыков и заметок",
        ]:
            tb.insert("end", f"  •  {line}\n", "bullet")

        tb.insert("end", "Как пользоваться\n", "h2")
        for i, line in enumerate([
            "Вкладка «Предметы» — задай цены на ресурсы (ПКМ по строке)",
            "Вкладка «Навыки» — выставь свои уровни",
            "Вкладка «Рецепты» — выбери рецепт, увидишь расчёт",
            "Тумблер «Закупка | Крафт» — переключи режим подсчёта",
            "Впиши цену продажи — увидишь чистую прибыль",
        ], 1):
            tb.insert("end", f"  {i}.  {line}\n", "bullet")

        tb.insert("end", "─" * 68 + "\n", "sep")
        tb.insert("end", "Создатель  ·  ", "author")
        tb.insert("end", f"{APP_AUTHOR}\n", "author_val")

        tb.insert("end", "\n\n\n\n\n\n\n\n")
        dm_words = ["деманы", "деманы", "деманы", "меня", "не", "одолели",
                    "деманы", "деманы", "деманы"]
        for i, w in enumerate(dm_words):
            tag = f"dm_{i}"
            color = dm_palette[i % len(dm_palette)]
            inner.tag_configure(tag, foreground=color,
                                font=(F_DISPLAY, 8))
            tb.insert("end", w + " ", tag)

        lock_text_selection(tb)


class SupportWindow(FloatingWindow):
    def __init__(self, parent):
        super().__init__(parent, "Техподдержка", 420, 260, resizable=False)

        outer = ctk.CTkFrame(self, fg_color=C_BG)
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(outer, text="Связаться с поддержкой",
                     text_color=C_TEXT, font=(F_DISPLAY, 13, "bold"),
                     anchor="w").pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(outer,
                     text="Если что-то сломалось, нашёл баг "
                          "или есть идея — пиши в любой из каналов.",
                     text_color=C_TEXT_DIM, font=(F_DISPLAY, 11),
                     anchor="w", wraplength=380, justify="left"
                     ).pack(fill="x", pady=(0, 14))

        def row(label, value, url):
            block = ctk.CTkFrame(outer, fg_color=C_SURFACE_2,
                                 corner_radius=10,
                                 border_width=1, border_color=C_BORDER,
                                 height=52)
            block.pack(fill="x", pady=4)
            block.pack_propagate(False)

            left = ctk.CTkFrame(block, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True,
                      padx=(14, 0), pady=8)

            ctk.CTkLabel(left, text=label, text_color=C_TEXT_MUT,
                         font=(F_DISPLAY, 10), anchor="w"
                         ).pack(anchor="w")
            ctk.CTkLabel(left, text=value, text_color=C_TEXT,
                         font=(F_MONO, 11), anchor="w"
                         ).pack(anchor="w")

            ctk.CTkButton(
                block, text="Открыть",
                command=lambda u=url: webbrowser.open(u),
                fg_color=C_SURFACE_3, hover_color=C_SURFACE_4,
                text_color=C_ACCENT, corner_radius=6, height=30,
                width=90, font=(F_DISPLAY, 11, "bold")
            ).pack(side="right", padx=(0, 10), pady=11)

        row("Discord", SUPPORT_DISCORD, SUPPORT_DISCORD)
        row("Telegram", SUPPORT_TELEGRAM, SUPPORT_TELEGRAM)


class StalzoneMain(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=C_BG)
        self.title(APP_NAME)
        self.geometry("1320x860")
        self.minsize(1100, 660)

        pick_fonts()

        self.items_all = {}
        self.items = {}
        self.recipes = []
        self.calc = None
        self.user_skills = {}

        self._items_query = None
        self._recipes_query = None
        self._items_sort_idx = 0
        self._recipes_sort_idx = 0
        self._station_filter = None
        self._station_chips = {}

        self._active_tab = None
        self._tab_pages = {}
        self._tab_buttons = {}
        self._ui_built = False

        self._item_search_timer = None
        self._recipe_search_timer = None

        self._skill_steppers = {}
        self._skills_scroll = None
        self._skills_summary = None
        self._skills_built = False

        self.items_list = None
        self.recipes_list = None

        self._photo_cache = {}
        self._active_menu = None
        self._skill_icon_images = {}

        self.sale_prices = {}
        self._selected_recipe = None

        self._anim_phase = 0.0
        self._anim_alive = True

        self._win_resize_timer = None
        self._anim_paused = False

        self._notes_win = None
        self._calc_win = None
        self._info_win = None
        self._support_win = None

        self._calc_mode = "buy"

        self._setup_window_icon()
        self.deiconify()
        self.update_idletasks()

        self._build_loading_screen()
        self.after(150, self._initial_load)

        self.bind("<Configure>", self._on_root_configure, add="+")

    def _on_root_configure(self, event):
        if event.widget is not self:
            return
        self._anim_paused = True
        if self._win_resize_timer is not None:
            try:
                self.after_cancel(self._win_resize_timer)
            except Exception:
                pass
        self._win_resize_timer = self.after(150, self._resume_anim)

    def _resume_anim(self):
        self._win_resize_timer = None
        self._anim_paused = False

    def _setup_window_icon(self):
        try:
            if not APP_ICO.exists():
                pil = create_window_icon(256)
                pil.save(APP_ICO, format="ICO",
                         sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                (64, 64), (128, 128), (256, 256)])
            self.iconbitmap(str(APP_ICO))
            self.wm_iconbitmap(str(APP_ICO))
        except Exception as e:
            print(f"[main] иконка: {e}")

    def _get_skill_icon(self, skill_name, size=42):
        if skill_name in self._skill_icon_images:
            return self._skill_icon_images[skill_name]
        try:
            pil = create_skill_icon(skill_name, size)
            img = ctk.CTkImage(light_image=pil, dark_image=pil,
                               size=(size, size))
            self._skill_icon_images[skill_name] = img
            return img
        except Exception as e:
            print(f"[skill_icon] {e}")
            return None

    def _build_loading_screen(self):
        self._loading_frame = ctk.CTkFrame(self, fg_color=C_BG)
        self._loading_frame.pack(fill="both", expand=True)
        center = ctk.CTkFrame(self._loading_frame, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        logo_pil = create_logo_image(96)
        self._logo_img = ctk.CTkImage(
            light_image=logo_pil, dark_image=logo_pil, size=(72, 72))
        ctk.CTkLabel(center, image=self._logo_img, text="").pack(pady=(0, 20))

        ctk.CTkLabel(center, text=APP_NAME.upper(), text_color=C_TEXT,
                     font=(F_DISPLAY, 26, "bold")).pack()
        ctk.CTkLabel(center, text="К А Л Ь К У Л Я Т О Р   У Б Е Ж И Щ А",
                     text_color=C_ACCENT,
                     font=(F_DISPLAY, 11)).pack(pady=(6, 30))

        self._load_status = ctk.CTkLabel(
            center, text="Загрузка базы…", text_color=C_TEXT_DIM,
            font=(F_DISPLAY, 12))
        self._load_status.pack(pady=(0, 12))
        self._load_bar = ctk.CTkProgressBar(
            center, width=420, height=6,
            fg_color=C_SURFACE_2, progress_color=C_ACCENT, corner_radius=3)
        self._load_bar.set(0)
        self._load_bar.pack()

    def _loading_progress(self, done, total):
        try:
            frac = 0 if total == 0 else min(1.0, done / total)
            self._load_bar.set(frac)
            self._load_status.configure(text=f"Загрузка базы… {done} / {total}")
            self.update_idletasks()
        except Exception:
            pass

    def _loading_message(self, text):
        try:
            self._load_status.configure(text=text)
            self.update_idletasks()
        except Exception:
            pass

    def _initial_load(self):
        print("[main] старт")
        try:
            self.items_all = load_items(
                progress_callback=self._loading_progress)
        except Exception as e:
            self._show_error("Ошибка загрузки базы", str(e))
            self.items_all = {}
        print(f"[main] всего в базе: {len(self.items_all)}")

        self._loading_message("Чтение рецептов…")
        raw = load_hideout_recipes()

        def _norm(iid: str) -> str:
            if not iid:
                return iid
            if iid in self.items_all:
                return iid
            if "_" in iid:
                base = iid.rsplit("_", 1)[0]
                if base in self.items_all:
                    return base
            return iid

        self.recipes = []
        for r in raw:
            try:
                self.recipes.append(CraftRecipe(
                    recipe_id=r["id"],
                    station=r.get("station", "—"),
                    level=r.get("level", 0),
                    duration=r.get("duration", 0),
                    ingredients=[
                        CraftIngredient(item_id=_norm(req["itemId"]),
                                        count=req.get("count", 1))
                        for req in r.get("requirements", [])
                        if "itemId" in req
                    ],
                    product_id=_norm(r["productId"]),
                    product_count=r.get("productCount", 1),
                    skill=r.get("skill", ""),
                    skill_level=r.get("skill_level", 0),
                ))
            except Exception:
                continue
        print(f"[main] рецептов: {len(self.recipes)}")

        self._loading_message("Чтение навыков…")
        self._load_skills()

        self._build_items_from_recipes()
        names = {iid: meta["name"] for iid, meta in self.items_all.items()}
        self.calc = HideoutCalculator(names, self.recipes)

        self._loading_message("Чтение цен…")
        self._load_prices()
        self._load_sale_prices()

        self._loading_message("Подготовка интерфейса…")
        self.icon_mgr = IconManager(ICONS_CACHE, size=(22, 22))

        print("[main] строю UI")
        self._loading_frame.destroy()
        self._build_ui()
        self._ui_built = True

        self.after(120, self._refresh_skills_page)
        self.after(80, self._initial_render)
        self.after(300, self._initial_render)
        self.after(700, self._initial_render)
        self.after(60, self._animate_accent)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(400, self._poll_icons)
        print("[main] готово")

    def _animate_accent(self):
        if not self._anim_alive:
            return
        if not self._anim_paused:
            try:
                t = (math.sin(self._anim_phase) + 1) * 0.5
                c1 = (0x38, 0xbd, 0xf8)
                c2 = (0xa7, 0x8b, 0xfa)
                self._accent_line.configure(fg_color=_lerp_color(c1, c2, t))
                if hasattr(self, "_live_dot"):
                    self._live_dot.configure(
                        text_color=_lerp_color((0x38, 0xbd, 0xf8),
                                               (0xa7, 0x8b, 0xfa), t))
            except Exception:
                pass
        self._anim_phase += 0.07
        if self._anim_phase > math.tau:
            self._anim_phase -= math.tau
        self.after(40, self._animate_accent)

    def _initial_render(self):
        try:
            self.update_idletasks()
        except Exception:
            pass
        if self.items_list is not None:
            self.items_list.redraw()
        if self.recipes_list is not None:
            self.recipes_list.redraw()

    def _build_items_from_recipes(self):
        if not self.recipes:
            self.items = {}
            return
        needed = set()
        for r in self.recipes:
            needed.add(r.product_id)
            for ing in r.ingredients:
                needed.add(ing.item_id)
        matched = {k: v for k, v in self.items_all.items() if k in needed}
        missing = needed - set(matched.keys())
        self.items = matched
        print(f"[main] найдено предметов: {len(matched)} из {len(needed)}")
        if missing:
            print(f"[main] ⚠ не найдено {len(missing)} ID:")
            for x in sorted(missing)[:20]:
                print(f"    НЕТ: {x}")
        fixed = 0
        for iid, meta in self.items.items():
            if meta.get("icon"):
                continue
            cat = (meta.get("category") or "").strip("/")
            meta["icon"] = (f"{ICON_BASE}/{cat}/{iid}.png" if cat
                            else f"{ICON_BASE}/{iid}.png")
            fixed += 1
        if fixed:
            print(f"[main] URL иконок: {fixed}")

    def _all_skills(self):
        base = list(ALL_SKILLS)
        extra = sorted({r.skill for r in self.recipes
                        if r.skill and r.skill not in base})
        return base + extra

    def _load_skills(self):
        if not SKILLS_FILE.exists():
            return
        try:
            with open(SKILLS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                try:
                    val = int(v)
                except (TypeError, ValueError):
                    continue
                self.user_skills[k] = max(SKILL_MIN, min(SKILL_MAX, val))
        except Exception as e:
            print(f"[skills] {e}")

    def _save_skills(self):
        try:
            with open(SKILLS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.user_skills, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _get_skill_level(self, skill):
        if skill not in self.user_skills:
            self.user_skills[skill] = SKILL_DEFAULT
        return self.user_skills[skill]

    def _is_recipe_available(self, recipe):
        if not recipe.skill or recipe.skill_level <= 0:
            return True
        return self._get_skill_level(recipe.skill) >= recipe.skill_level

    def _recipe_lock_reason(self, recipe):
        if self._is_recipe_available(recipe):
            return ""
        return (f"{recipe.skill} {recipe.skill_level} · "
                f"у вас {self._get_skill_level(recipe.skill)}")

    def _on_skill_changed(self, skill, new_val):
        self.user_skills[skill] = new_val
        self._save_skills()
        self._recipes_query = None
        self._refresh_recipes(force=True)
        self._update_skills_summary()

    def _load_prices(self):
        if not PRICES_FILE.exists():
            return
        try:
            with open(PRICES_FILE, "r", encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    self.calc.set_price(k, float(v))
            print(f"[prices] загружено: {len(self.calc.prices)}")
        except Exception:
            pass

    def _save_prices(self):
        try:
            with open(PRICES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.calc.prices, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_sale_prices(self):
        if not SALE_PRICES_FILE.exists():
            return
        try:
            with open(SALE_PRICES_FILE, "r", encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    self.sale_prices[k] = float(v)
            print(f"[sale] загружено: {len(self.sale_prices)}")
        except Exception as e:
            print(f"[sale] {e}")

    def _save_sale_prices(self):
        try:
            with open(SALE_PRICES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.sale_prices, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self):
        self._anim_alive = False
        self._close_menu()
        if self.calc:
            self._save_prices()
            self._save_sale_prices()
        self._save_skills()
        for w in (self._notes_win, self._calc_win,
                  self._info_win, self._support_win):
            if w is not None:
                try:
                    w.destroy()
                except Exception:
                    pass
        self.destroy()

    def _close_menu(self):
        m = self._active_menu
        self._active_menu = None
        if m is not None:
            try:
                m.close()
            except Exception:
                pass

    def _on_menu_close(self, menu):
        if self._active_menu is menu:
            self._active_menu = None

    def _show_error(self, title, message):
        dlg = ModernDialog(self, title, 360, 200)
        ctk.CTkLabel(dlg.body, text=message, text_color=C_TEXT,
                     font=(F_DISPLAY, 12),
                     wraplength=320, justify="center"
                     ).pack(pady=(14, 14), fill="x")
        ctk.CTkButton(dlg.footer, text="OK", command=dlg._close,
                      fg_color=C_ACCENT, hover_color=C_ACCENT_H,
                      text_color="#0a0e14", corner_radius=8, height=36,
                      font=(F_DISPLAY, 12, "bold")).pack(fill="x")
        dlg.show()

    def _confirm(self, title, message, ok_text="OK", cancel_text="Отмена"):
        dlg = ModernDialog(self, title, 380, 180)
        result = {"ok": False}

        ctk.CTkLabel(dlg.body, text=message, text_color=C_TEXT,
                     font=(F_DISPLAY, 12),
                     wraplength=330, justify="center"
                     ).pack(pady=(12, 12), fill="x")

        wrap = ctk.CTkFrame(dlg.footer, fg_color="transparent")
        wrap.pack(fill="x")
        wrap.grid_columnconfigure(0, weight=1, uniform="btn")
        wrap.grid_columnconfigure(1, weight=1, uniform="btn")

        def ok():
            result["ok"] = True
            dlg._close()

        ctk.CTkButton(wrap, text=cancel_text, command=dlg._on_cancel,
                      fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
                      text_color=C_TEXT, corner_radius=8, height=36,
                      border_width=1, border_color=C_BORDER,
                      font=(F_DISPLAY, 12)
                      ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(wrap, text=ok_text, command=ok,
                      fg_color=C_ACCENT, hover_color=C_ACCENT_H,
                      text_color="#0a0e14", corner_radius=8, height=36,
                      font=(F_DISPLAY, 12, "bold")
                      ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        dlg.show()
        return result["ok"]

    def _toggle_window(self, attr: str, factory):
        w = getattr(self, attr)
        if w is not None:
            try:
                if w.winfo_exists():
                    w.deiconify()
                    w.lift()
                    w.focus_force()
                    return
            except Exception:
                pass
        setattr(self, attr, factory(self))

    def _open_notes(self):
        self._toggle_window("_notes_win", NotesWindow)

    def _open_calc(self):
        self._toggle_window("_calc_win", CalculatorWindow)

    def _open_info(self):
        self._toggle_window("_info_win", InfoWindow)

    def _open_support(self):
        self._toggle_window("_support_win", SupportWindow)

    def _on_calc_mode_change(self, mode_label: str):
        self._calc_mode = "buy" if mode_label == "Закупка" else "craft"
        if self._selected_recipe is not None:
            self._on_recipe_click(self._selected_recipe.recipe_id)

    def _build_ui(self):
        self.status_var = tk.StringVar()
        self._reset_status()

        sidebar = ctk.CTkFrame(self, fg_color=C_SIDEBAR,
                               corner_radius=0, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_block = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_block.pack(fill="x", padx=20, pady=(24, 28))
        row1 = ctk.CTkFrame(logo_block, fg_color="transparent")
        row1.pack(fill="x")

        logo_small = create_logo_image(64)
        self._logo_small = ctk.CTkImage(
            light_image=logo_small, dark_image=logo_small, size=(34, 34))
        ctk.CTkLabel(row1, image=self._logo_small, text=""
                     ).pack(side="left", padx=(0, 10))

        txt = ctk.CTkFrame(row1, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(txt, text="STALZONE", text_color=C_TEXT,
                     font=(F_DISPLAY, 15, "bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(txt, text="M A I N", text_color=C_ACCENT,
                     font=(F_DISPLAY, 10), anchor="w"
                     ).pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(logo_block, text="калькулятор убежища",
                     text_color=C_TEXT_MUT, font=(F_DISPLAY, 10),
                     anchor="w").pack(fill="x", pady=(8, 0))

        tk.Frame(sidebar, bg=C_BORDER, height=1).pack(fill="x", padx=20)

        tabs_block = ctk.CTkFrame(sidebar, fg_color="transparent")
        tabs_block.pack(fill="x", padx=10, pady=(12, 0))

        self._tab_buttons["items"] = SidebarTab(
            tabs_block, "items", "Предметы", "▤", self._switch_tab)
        self._tab_buttons["items"].pack(fill="x", pady=2)
        self._tab_buttons["recipes"] = SidebarTab(
            tabs_block, "recipes", "Рецепты", "✦", self._switch_tab)
        self._tab_buttons["recipes"].pack(fill="x", pady=2)
        self._tab_buttons["skills"] = SidebarTab(
            tabs_block, "skills", "Навыки", "⚙", self._switch_tab)
        self._tab_buttons["skills"].pack(fill="x", pady=2)

        bottom_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom_box.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        tools = ctk.CTkFrame(bottom_box, fg_color="transparent")
        tools.pack(fill="x")
        tools.grid_columnconfigure(0, weight=1, uniform="tools")
        tools.grid_columnconfigure(1, weight=1, uniform="tools")

        ctk.CTkButton(
            tools, text="📝  Заметки", command=self._open_notes,
            fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            text_color=C_TEXT, corner_radius=8, height=34,
            border_width=1, border_color=C_BORDER,
            font=(F_DISPLAY, 11)
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))

        ctk.CTkButton(
            tools, text="🧮  Кальк.", command=self._open_calc,
            fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            text_color=C_TEXT, corner_radius=8, height=34,
            border_width=1, border_color=C_BORDER,
            font=(F_DISPLAY, 11)
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        tk.Frame(bottom_box, bg=C_BORDER, height=1).pack(
            fill="x", padx=4, pady=6)

        ctk.CTkButton(
            bottom_box, text="🛟  Техподдержка",
            command=self._open_support,
            fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            text_color=C_TEXT, corner_radius=8, height=34,
            anchor="w", font=(F_DISPLAY, 11),
            border_width=1, border_color=C_BORDER
        ).pack(fill="x", pady=(0, 3))

        ctk.CTkButton(
            bottom_box, text="ⓘ  Информация",
            command=self._open_info,
            fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            text_color=C_TEXT, corner_radius=8, height=34,
            anchor="w", font=(F_DISPLAY, 11),
            border_width=1, border_color=C_BORDER
        ).pack(fill="x")

        ctk.CTkLabel(bottom_box, text=f"v{APP_VERSION}",
                     text_color=C_TEXT_MUT,
                     font=(F_MONO, 10), anchor="center"
                     ).pack(fill="x", pady=(8, 0))

        main_area = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        main_area.pack(side="left", fill="both", expand=True)

        topbar = ctk.CTkFrame(main_area, fg_color=C_BG,
                              corner_radius=0, height=58)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        self._page_title = ctk.CTkLabel(
            topbar, text="ПРЕДМЕТЫ", text_color=C_TEXT,
            font=(F_DISPLAY, 17, "bold"), anchor="w")
        self._page_title.pack(side="left", padx=24, pady=16)

        actions = ctk.CTkFrame(topbar, fg_color="transparent")
        actions.pack(side="right", padx=20, pady=12)
        self._chip_button(actions, "Импорт", self._on_import_prices)
        self._chip_button(actions, "Экспорт", self._on_export_prices)
        self._chip_button(actions, "Сброс", self._on_reset_prices)
        tk.Frame(actions, bg=C_BORDER, width=1, height=22).pack(
            side="left", padx=8, pady=6)
        self._chip_button(actions, "Сохранить", self._on_save_prices,
                          accent=True)

        self._accent_line = ctk.CTkFrame(
            main_area, fg_color=C_ACCENT, height=2, corner_radius=0)
        self._accent_line.pack(fill="x")

        self._content = ctk.CTkFrame(main_area, fg_color=C_BG, corner_radius=0)
        self._content.pack(fill="both", expand=True)

        self._tab_pages["items"] = self._build_items_page(self._content)
        self._tab_pages["recipes"] = self._build_recipes_page(self._content)
        self._tab_pages["skills"] = self._build_skills_page(self._content)

        status = ctk.CTkFrame(self, fg_color=C_BG,
                              corner_radius=0, height=26)
        status.pack(side="bottom", fill="x")
        status.pack_propagate(False)
        tk.Frame(status, bg=C_BORDER, height=1).pack(fill="x", side="top")

        self._live_dot = ctk.CTkLabel(
            status, text="●", text_color=C_ACCENT, font=(F_DISPLAY, 10))
        self._live_dot.pack(side="left", padx=(22, 6))

        ctk.CTkLabel(status, textvariable=self.status_var,
                     text_color=C_TEXT_MUT, font=(F_DISPLAY, 10),
                     anchor="w").pack(side="left")

        self._switch_tab("items")

    def _build_items_page(self, parent):
        page = ctk.CTkFrame(parent, fg_color=C_BG, corner_radius=0)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(18, 12))
        self._items_title = ctk.CTkLabel(
            header, text="Предметы крафта", text_color=C_TEXT,
            font=(F_DISPLAY, 13, "bold"), anchor="w")
        self._items_title.pack(side="left")
        self._items_hint = ctk.CTkLabel(
            header, text="", text_color=C_TEXT_MUT,
            font=(F_DISPLAY, 11))
        self._items_hint.pack(side="left", padx=(10, 0), pady=(3, 0))

        row = ctk.CTkFrame(page, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(0, 14))

        search_wrap = ctk.CTkFrame(
            row, fg_color=C_SURFACE_2, corner_radius=10, height=42,
            border_width=1, border_color=C_BORDER)
        search_wrap.pack(side="left", fill="x", expand=True)
        search_wrap.pack_propagate(False)
        ctk.CTkLabel(search_wrap, text="⌕", text_color=C_TEXT_DIM,
                     font=(F_DISPLAY, 18)).pack(side="left", padx=(14, 0))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write",
                                  lambda *_: self._on_search_changed())
        e = ctk.CTkEntry(
            search_wrap, textvariable=self.search_var,
            placeholder_text="Найти предмет…",
            fg_color="transparent", border_width=0,
            text_color=C_TEXT, placeholder_text_color=C_TEXT_MUT,
            font=(F_DISPLAY, 12))
        e.pack(side="left", fill="both", expand=True, padx=(6, 12))
        e.bind("<FocusIn>", lambda _e: search_wrap.configure(
            border_color=C_ACCENT))
        e.bind("<FocusOut>", lambda _e: search_wrap.configure(
            border_color=C_BORDER))
        self.search_entry = e

        self.items_sort_btn = ctk.CTkButton(
            row, text=ITEMS_SORT_CYCLE[self._items_sort_idx][0],
            command=self._cycle_items_sort,
            width=120, height=42,
            fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            text_color=C_ACCENT, corner_radius=10,
            border_width=1, border_color=C_BORDER,
            font=(F_DISPLAY, 12, "bold"))
        self.items_sort_btn.pack(side="right", padx=(8, 0))

        list_wrap = ctk.CTkFrame(page, fg_color=C_SURFACE, corner_radius=12)
        list_wrap.pack(fill="both", expand=True, padx=24, pady=(0, 18))

        self.items_list = CanvasList(list_wrap, row_height=46, kind="item")
        self.items_list.pack(fill="both", expand=True, padx=6, pady=6)

        self._refresh_items(force=True)
        return page

    def _build_recipes_page(self, parent):
        page = ctk.CTkFrame(parent, fg_color=C_BG, corner_radius=0)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        chips_wrap = ctk.CTkFrame(page, fg_color="transparent")
        chips_wrap.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 8))
        stations = sorted({r.station for r in self.recipes})
        self._add_chip(chips_wrap, "Все", None)
        for s in stations[:10]:
            self._add_chip(chips_wrap, s, s)

        row = ctk.CTkFrame(page, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 10))

        search_wrap = ctk.CTkFrame(
            row, fg_color=C_SURFACE_2, corner_radius=10, height=42,
            border_width=1, border_color=C_BORDER)
        search_wrap.pack(side="left", fill="x", expand=True)
        search_wrap.pack_propagate(False)
        ctk.CTkLabel(search_wrap, text="⌕", text_color=C_TEXT_DIM,
                     font=(F_DISPLAY, 18)).pack(side="left", padx=(14, 0))
        self.recipe_search_var = tk.StringVar()
        self.recipe_search_var.trace_add(
            "write", lambda *_: self._on_recipe_search_changed())
        e = ctk.CTkEntry(
            search_wrap, textvariable=self.recipe_search_var,
            placeholder_text="Найти рецепт по названию продукта…",
            fg_color="transparent", border_width=0,
            text_color=C_TEXT, placeholder_text_color=C_TEXT_MUT,
            font=(F_DISPLAY, 12))
        e.pack(side="left", fill="both", expand=True, padx=(6, 12))
        e.bind("<FocusIn>", lambda _e: search_wrap.configure(
            border_color=C_ACCENT))
        e.bind("<FocusOut>", lambda _e: search_wrap.configure(
            border_color=C_BORDER))
        self.recipe_search_entry = e

        self.recipes_sort_btn = ctk.CTkButton(
            row, text=RECIPES_SORT_CYCLE[self._recipes_sort_idx][0],
            command=self._cycle_recipes_sort,
            width=130, height=42,
            fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            text_color=C_ACCENT, corner_radius=10,
            border_width=1, border_color=C_BORDER,
            font=(F_DISPLAY, 12, "bold"))
        self.recipes_sort_btn.pack(side="right", padx=(8, 0))

        list_wrap = ctk.CTkFrame(page, fg_color=C_SURFACE, corner_radius=12)
        list_wrap.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 8))

        self.recipes_list = CanvasList(list_wrap, row_height=52, kind="recipe")
        self.recipes_list.pack(fill="both", expand=True, padx=6, pady=6)

        bottom = ctk.CTkFrame(page, fg_color=C_SURFACE,
                              corner_radius=12, height=320)
        bottom.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 18))
        bottom.pack_propagate(False)
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_rowconfigure(1, weight=1)

        bh = ctk.CTkFrame(bottom, fg_color="transparent")
        bh.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 6))
        ctk.CTkLabel(bh, text="ДЕТАЛИЗАЦИЯ", text_color=C_TEXT,
                     font=(F_DISPLAY, 13, "bold")).pack(side="left")
        ctk.CTkLabel(bh, text="выберите рецепт выше",
                     text_color=C_TEXT_MUT,
                     font=(F_DISPLAY, 11)).pack(side="left",
                                                padx=(12, 0), pady=(3, 0))

        self._calc_mode_var = tk.StringVar(value="Закупка")
        ctk.CTkSegmentedButton(
            bh,
            values=["Закупка", "Крафт"],
            variable=self._calc_mode_var,
            command=self._on_calc_mode_change,
            fg_color=C_SURFACE_3,
            selected_color=C_ACCENT,
            selected_hover_color=C_ACCENT_H,
            unselected_color=C_SURFACE_3,
            unselected_hover_color=C_SURFACE_4,
            text_color=C_TEXT,
            font=(F_DISPLAY, 11),
            height=28,
        ).pack(side="right")

        self.detail_text = ctk.CTkTextbox(
            bottom, fg_color=C_SURFACE_2, corner_radius=10,
            text_color=C_TEXT, border_width=0,
            font=(F_MONO, 12),
            scrollbar_button_color=C_SURFACE_3,
            scrollbar_button_hover_color=C_ACCENT_D)
        self.detail_text.grid(row=1, column=0, sticky="nsew",
                              padx=14, pady=(0, 8))

        inner = self.detail_text._textbox
        inner.tag_configure("title", foreground=C_ACCENT)
        inner.tag_configure("dim", foreground=C_TEXT_DIM)
        inner.tag_configure("muted", foreground=C_TEXT_MUT)
        inner.tag_configure("ok", foreground=C_OK)
        inner.tag_configure("bad", foreground=C_BAD)
        inner.tag_configure("warn", foreground=C_WARN)
        inner.tag_configure("total", foreground=C_ACCENT)
        inner.tag_configure("craft_tag", foreground=C_ACCENT_P)

        lock_text_selection(self.detail_text)

        sale_panel = ctk.CTkFrame(
            bottom, fg_color=C_SURFACE_2, corner_radius=10,
            border_width=1, border_color=C_BORDER)
        sale_panel.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

        ctk.CTkLabel(sale_panel, text="Цена продажи за ед.",
                     text_color=C_TEXT_DIM, font=(F_DISPLAY, 11),
                     anchor="w").pack(side="left", padx=(14, 8), pady=12)

        self.sale_var = tk.StringVar()
        self.sale_entry = ctk.CTkEntry(
            sale_panel, textvariable=self.sale_var,
            fg_color=C_BG, border_color=C_BORDER, border_width=1,
            corner_radius=6, height=32, width=140,
            text_color=C_ACCENT, font=(F_MONO, 13, "bold"),
            justify="center")
        self.sale_entry.pack(side="left", padx=(0, 16), pady=12)
        self.sale_var.trace_add("write", lambda *_: self._on_sale_change())

        hands_box = ctk.CTkFrame(sale_panel, fg_color="transparent")
        hands_box.pack(side="right", padx=(0, 24), pady=8)
        ctk.CTkLabel(hands_box, text="С рук (0%)",
                     text_color=C_TEXT_MUT, font=(F_DISPLAY, 10),
                     anchor="w").pack(anchor="w")
        self._profit_hands = ctk.CTkLabel(
            hands_box, text="—", text_color=C_TEXT_MUT,
            font=(F_MONO, 14, "bold"), anchor="w")
        self._profit_hands.pack(anchor="w")

        auc_box = ctk.CTkFrame(sale_panel, fg_color="transparent")
        auc_box.pack(side="right", padx=(0, 20), pady=8)
        ctk.CTkLabel(auc_box, text="Аукцион (5%)",
                     text_color=C_TEXT_MUT, font=(F_DISPLAY, 10),
                     anchor="w").pack(anchor="w")
        self._profit_auction = ctk.CTkLabel(
            auc_box, text="—", text_color=C_TEXT_MUT,
            font=(F_MONO, 14, "bold"), anchor="w")
        self._profit_auction.pack(anchor="w")

        self._refresh_recipes(force=True)
        return page

    def _build_skills_page(self, parent):
        page = ctk.CTkFrame(parent, fg_color=C_BG, corner_radius=0)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 12))
        ctk.CTkLabel(header, text="Уровни навыков", text_color=C_TEXT,
                     font=(F_DISPLAY, 13, "bold")).pack(side="left")
        self._skills_summary = ctk.CTkLabel(
            header, text="", text_color=C_TEXT_MUT,
            font=(F_DISPLAY, 11))
        self._skills_summary.pack(side="left", padx=(12, 0), pady=(3, 0))
        ctk.CTkButton(
            header, text="Сбросить все", command=self._reset_skills,
            fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            text_color=C_TEXT, corner_radius=8, height=32,
            border_width=1, border_color=C_BORDER,
            font=(F_DISPLAY, 11), width=130).pack(side="right")

        list_wrap = ctk.CTkFrame(page, fg_color=C_SURFACE, corner_radius=12)
        list_wrap.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 18))

        self._skills_scroll = ctk.CTkScrollableFrame(
            list_wrap, fg_color=C_SURFACE, corner_radius=0,
            scrollbar_button_color=C_SURFACE_3,
            scrollbar_button_hover_color=C_ACCENT_D)
        self._skills_scroll.pack(fill="both", expand=True, padx=6, pady=6)

        return page

    def _refresh_skills_page(self):
        if self._skills_scroll is None:
            return
        for child in self._skills_scroll.winfo_children():
            child.destroy()
        self._skill_steppers.clear()

        skills = self._all_skills()
        counts = {}
        for r in self.recipes:
            if r.skill and r.skill_level > 0:
                counts[r.skill] = counts.get(r.skill, 0) + 1

        for skill in skills:
            row = ctk.CTkFrame(self._skills_scroll, fg_color=C_SURFACE_2,
                               corner_radius=10, height=62,
                               border_width=1, border_color=C_BORDER)
            row.pack(fill="x", padx=10, pady=5)
            row.pack_propagate(False)

            icon_img = self._get_skill_icon(skill, size=42)
            if icon_img is not None:
                ctk.CTkLabel(row, image=icon_img, text="",
                             width=42, height=42
                             ).pack(side="left", padx=(12, 10), pady=10)
            else:
                ctk.CTkLabel(
                    row, text=skill[0] if skill else "?",
                    width=42, height=42,
                    fg_color=C_ACCENT_D, text_color="#ffffff",
                    corner_radius=10, font=(F_DISPLAY, 15, "bold")
                ).pack(side="left", padx=(12, 10), pady=10)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(left, text=skill, text_color=C_TEXT,
                         font=(F_DISPLAY, 13, "bold"),
                         anchor="w").pack(anchor="w")

            req = counts.get(skill, 0)
            ctk.CTkLabel(left,
                         text=(f"требуется в {req} рецепт(ах)" if req
                               else "навык не используется в рецептах"),
                         text_color=C_TEXT_MUT,
                         font=(F_DISPLAY, 10), anchor="w"
                         ).pack(anchor="w", pady=(1, 0))

            stepper = SkillStepper(
                row, skill, value=self._get_skill_level(skill),
                on_change=self._on_skill_changed,
                min_val=SKILL_MIN, max_val=SKILL_MAX)
            stepper.pack(side="right", padx=(0, 12))
            self._skill_steppers[skill] = stepper

        self._skills_built = True
        self._update_skills_summary()

    def _update_skills_summary(self):
        if self._skills_summary is None:
            return
        total = len(self.recipes)
        locked = sum(1 for r in self.recipes
                     if not self._is_recipe_available(r))
        avail = total - locked
        if total == 0:
            self._skills_summary.configure(text="рецептов нет")
        else:
            self._skills_summary.configure(
                text=f"доступно {avail} из {total}  ·  заблокировано {locked}")

    def _reset_skills(self):
        if not self._confirm("Сбросить навыки",
                             f"Установить всем навыкам уровень {SKILL_DEFAULT}?",
                             ok_text="Сбросить"):
            return
        self.user_skills.clear()
        for skill in self._all_skills():
            self.user_skills[skill] = SKILL_DEFAULT
        self._save_skills()
        self._refresh_skills_page()
        self._recipes_query = None
        self._refresh_recipes(force=True)

    def _switch_tab(self, key):
        if key == self._active_tab:
            return
        self._active_tab = key

        for k, page in self._tab_pages.items():
            if k == key:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()

        for k, btn in self._tab_buttons.items():
            btn.set_active(k == key)

        titles = {"items": "ПРЕДМЕТЫ", "recipes": "РЕЦЕПТЫ",
                  "skills": "НАВЫКИ"}
        self._page_title.configure(text=titles.get(key, ""))

        if key == "skills" and not self._skills_built:
            self._refresh_skills_page()
        elif key == "items" and self.items_list is not None:
            self.after(30, self.items_list.smart_redraw)
        elif key == "recipes" and self.recipes_list is not None:
            self.after(30, self.recipes_list.smart_redraw)

    def _chip_button(self, parent, text, command, accent=False):
        if accent:
            return ctk.CTkButton(
                parent, text=text, command=command,
                fg_color=C_ACCENT, hover_color=C_ACCENT_H,
                text_color="#0a0e14", corner_radius=8, height=34,
                font=(F_DISPLAY, 12, "bold"), width=115)
        return ctk.CTkButton(
            parent, text=text, command=command,
            fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
            text_color=C_TEXT, corner_radius=8, height=34,
            border_width=1, border_color=C_BORDER,
            font=(F_DISPLAY, 12), width=92)

    def _add_chip(self, parent, label, station):
        is_active = station is None
        btn = ctk.CTkButton(
            parent, text=label,
            command=lambda s=station: self._set_station_filter(s),
            fg_color=C_ACCENT if is_active else C_SURFACE_2,
            hover_color=C_ACCENT_H if is_active else C_SURFACE_3,
            text_color="#0a0e14" if is_active else C_TEXT_DIM,
            corner_radius=8, height=30,
            font=(F_DISPLAY, 11, "bold" if is_active else "normal"),
            width=0)
        btn.pack(side="left", padx=(0, 5))
        self._station_chips[station or "__all__"] = btn

    def _set_station_filter(self, station):
        self._station_filter = station
        for key, btn in self._station_chips.items():
            active = (station is None and key == "__all__") or key == station
            btn.configure(
                fg_color=C_ACCENT if active else C_SURFACE_2,
                hover_color=C_ACCENT_H if active else C_SURFACE_3,
                text_color="#0a0e14" if active else C_TEXT_DIM,
                font=(F_DISPLAY, 11, "bold" if active else "normal"))
        self._recipes_query = None
        self._refresh_recipes(force=True)

    def _cycle_items_sort(self):
        self._items_sort_idx = (self._items_sort_idx + 1) % len(ITEMS_SORT_CYCLE)
        self.items_sort_btn.configure(
            text=ITEMS_SORT_CYCLE[self._items_sort_idx][0])
        self._refresh_items(force=True)

    def _cycle_recipes_sort(self):
        self._recipes_sort_idx = (self._recipes_sort_idx + 1) % len(RECIPES_SORT_CYCLE)
        self.recipes_sort_btn.configure(
            text=RECIPES_SORT_CYCLE[self._recipes_sort_idx][0])
        self._refresh_recipes(force=True)

    def _apply_items_sort(self, arr):
        key = ITEMS_SORT_CYCLE[self._items_sort_idx][1]
        if key == "name_asc":
            return sorted(arr, key=lambda x: x[1]["name"])
        if key == "name_desc":
            return sorted(arr, key=lambda x: x[1]["name"], reverse=True)
        if key == "price_asc":
            return sorted(arr, key=lambda x: (
                self.calc.prices.get(x[0])
                if self.calc.prices.get(x[0]) is not None
                else float("inf")))
        if key == "price_desc":
            return sorted(arr, key=lambda x: (
                -self.calc.prices.get(x[0])
                if self.calc.prices.get(x[0]) is not None
                else float("-inf")))
        return arr

    def _apply_recipes_sort(self, arr):
        key = RECIPES_SORT_CYCLE[self._recipes_sort_idx][1]
        if key == "name_asc":
            return sorted(arr, key=lambda r: self.calc.items.get(
                r.product_id, "").lower())
        if key == "name_desc":
            return sorted(arr, key=lambda r: self.calc.items.get(
                r.product_id, "").lower(), reverse=True)
        if key == "avail_first":
            return sorted(arr, key=lambda r: (
                0 if self._is_recipe_available(r) else 1,
                self.calc.items.get(r.product_id, "").lower()))
        if key == "locked_first":
            return sorted(arr, key=lambda r: (
                0 if not self._is_recipe_available(r) else 1,
                self.calc.items.get(r.product_id, "").lower()))
        return arr

    def _get_photo(self, url, name):
        if not url:
            return None
        if url in self._photo_cache:
            return self._photo_cache[url]
        try:
            photo = self.icon_mgr.get_tk(url, name)
            if photo is not None:
                self._photo_cache[url] = photo
            return photo
        except Exception:
            return None

    def _on_search_changed(self):
        if self._item_search_timer is not None:
            try:
                self.after_cancel(self._item_search_timer)
            except Exception:
                pass
        self._item_search_timer = self.after(200, self._refresh_items)

    def _refresh_items(self, force=False):
        self._item_search_timer = None
        query = self.search_var.get().lower().strip()
        sort_key = ITEMS_SORT_CYCLE[self._items_sort_idx][1]
        cache_key = (query, sort_key)
        if not force and cache_key == self._items_query:
            return
        self._items_query = cache_key

        if self.recipes:
            self._items_hint.configure(
                text=f"только то, что участвует в {len(self.recipes)} рецептах")
        else:
            self._items_hint.configure(text="рецепты не добавлены")

        all_items = list(self.items.items())
        if query:
            all_items = [(iid, meta) for iid, meta in all_items
                         if query in meta["name"].lower()]
        all_items = self._apply_items_sort(all_items)

        def prep(item):
            iid, meta = item
            price = self.calc.prices.get(iid)
            icon_url = meta.get("icon", "")
            photo = self._get_photo(icon_url, meta["name"])
            return {
                "id": iid,
                "name": meta["name"],
                "value": (f"{price:,.0f}".replace(",", " ")
                          if price is not None else "—"),
                "value_color": C_OK if price is not None else C_TEXT_MUT,
                "icon_photo": photo,
                "icon_url": icon_url,
            }

        empty_msg = ""
        if not all_items:
            if not self.recipes:
                empty_msg = ("Рецептов нет.\n"
                             "Откройте recipes.json и добавьте рецепт.")
            elif query:
                empty_msg = f"По запросу «{query}» ничего не найдено."
            else:
                empty_msg = ("ID из recipes.json не найдены в базе.\n"
                             "Проверьте консоль.")

        if self.items_list is not None:
            self.items_list.set_data(
                all_items,
                on_click=lambda it: None,
                on_right_click=self._on_item_rclick,
                empty_message=empty_msg,
                prep=prep)

        self.status_var.set(f"Предметов: {len(all_items)}")

    def _on_item_rclick(self, event, item):
        self._close_menu()
        item_id = item[0]
        meta = self.items_all.get(item_id, {})
        name = meta.get("name", item_id)
        menu = ModernContextMenu(
            self,
            actions=[("💰   Задать цену",
                      lambda: self._ask_price(item_id, name))],
            x=event.x_root, y=event.y_root,
            on_close=self._on_menu_close)
        self._active_menu = menu

    def _ask_price(self, item_id, name):
        try:
            prev_focus = self.focus_get()
        except Exception:
            prev_focus = None

        dlg = ModernDialog(self, "Цена предмета", 380, 250)
        ctk.CTkLabel(dlg.body, text=name, text_color=C_TEXT,
                     font=(F_DISPLAY, 13, "bold"),
                     wraplength=320, justify="center"
                     ).pack(pady=(2, 2), fill="x")
        ctk.CTkLabel(dlg.body, text="Введите цену",
                     text_color=C_TEXT_MUT, font=(F_DISPLAY, 11)
                     ).pack(pady=(0, 6))

        var = tk.StringVar(value=str(self.calc.prices.get(item_id, "")))
        entry = ctk.CTkEntry(
            dlg.body, textvariable=var,
            fg_color=C_SURFACE_2, border_color=C_BORDER,
            border_width=1, corner_radius=8, height=42,
            text_color=C_ACCENT,
            font=(F_MONO, 15, "bold"), justify="center")
        entry.pack(fill="x", pady=(0, 2))
        entry.focus_set()
        entry.select_range(0, tk.END)

        error_label = ctk.CTkLabel(dlg.body, text="",
                                   text_color=C_BAD,
                                   font=(F_DISPLAY, 10))
        error_label.pack(pady=(0, 2))

        def save():
            raw = var.get().strip().replace(",", ".").replace(" ", "")
            if raw == "":
                self.calc.prices.pop(item_id, None)
            else:
                try:
                    self.calc.set_price(item_id, float(raw))
                except ValueError:
                    error_label.configure(text="Введите число")
                    return
            self._update_item_price(item_id)
            dlg._close()

        def delete():
            self.calc.prices.pop(item_id, None)
            self._update_item_price(item_id)
            dlg._close()

        dlg.footer.grid_columnconfigure(0, weight=1, uniform="btn")
        dlg.footer.grid_columnconfigure(1, weight=1, uniform="btn")
        dlg.footer.grid_columnconfigure(2, weight=1, uniform="btn")

        ctk.CTkButton(dlg.footer, text="Отмена", command=dlg._on_cancel,
                      fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
                      text_color=C_TEXT, corner_radius=8, height=36,
                      border_width=1, border_color=C_BORDER,
                      font=(F_DISPLAY, 12)
                      ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(dlg.footer, text="Удалить", command=delete,
                      fg_color=C_SURFACE_2, hover_color=C_SURFACE_3,
                      text_color=C_BAD, corner_radius=8, height=36,
                      border_width=1, border_color=C_BORDER,
                      font=(F_DISPLAY, 12)
                      ).grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkButton(dlg.footer, text="Сохранить", command=save,
                      fg_color=C_ACCENT, hover_color=C_ACCENT_H,
                      text_color="#0a0e14", corner_radius=8, height=36,
                      font=(F_DISPLAY, 12, "bold")
                      ).grid(row=0, column=2, sticky="ew", padx=(4, 0))

        dlg.bind("<Return>", lambda e: save())
        dlg.show()

        try:
            if prev_focus is not None and prev_focus.winfo_exists():
                prev_focus.focus_set()
            else:
                self.focus_force()
        except Exception:
            try:
                self.focus_force()
            except Exception:
                pass

    def _update_item_price(self, item_id):
        if self.items_list is None:
            return
        for idx, item in enumerate(self.items_list.items):
            if item[0] == item_id:
                price = self.calc.prices.get(item_id)
                value = (f"{price:,.0f}".replace(",", " ")
                         if price is not None else "—")
                color = C_OK if price is not None else C_TEXT_MUT
                self.items_list.update_value(idx, value, color)
                break
        if self._selected_recipe is not None:
            self._on_recipe_click(self._selected_recipe.recipe_id)

    def _on_recipe_search_changed(self):
        if self._recipe_search_timer is not None:
            try:
                self.after_cancel(self._recipe_search_timer)
            except Exception:
                pass
        self._recipe_search_timer = self.after(200, self._refresh_recipes)

    def _refresh_recipes(self, force=False):
        self._recipe_search_timer = None
        query = self.recipe_search_var.get().lower().strip()
        sort_key = RECIPES_SORT_CYCLE[self._recipes_sort_idx][1]
        cache_key = (query, self._station_filter, sort_key)
        if not force and cache_key == self._recipes_query:
            return
        self._recipes_query = cache_key

        filtered = list(self.recipes)
        if self._station_filter:
            filtered = [r for r in filtered
                        if r.station == self._station_filter]
        if query:
            filtered = [r for r in filtered
                        if query in self.calc.items.get(r.product_id,
                                                        "").lower()]
        filtered = self._apply_recipes_sort(filtered)

        def prep(recipe):
            product_name = self.calc.items.get(recipe.product_id,
                                               recipe.product_id)
            available = self._is_recipe_available(recipe)
            reason = self._recipe_lock_reason(recipe)
            chip_text = recipe.station
            if recipe.skill and recipe.skill_level > 0:
                chip_text += f"  ·  {recipe.skill} {recipe.skill_level}"
            elif recipe.skill:
                chip_text += f"  ·  {recipe.skill}"

            return {
                "chip": chip_text,
                "chip_color": C_ACCENT if available else C_BAD,
                "chip_bg": C_SURFACE_3 if available else "#3a1a1a",
                "bar_color": C_ACCENT if available else C_BAD,
                "name": product_name,
                "name_color": C_TEXT if available else C_TEXT_MUT,
                "count_str": f"×{recipe.product_count}",
                "count_color": C_ACCENT if available else C_TEXT_MUT,
                "reason": reason,
            }

        empty_msg = ""
        if not filtered:
            if not self.recipes:
                empty_msg = ("Рецепты не добавлены.\n"
                             "Откройте recipes.json и впишите рецепты.")
            elif query:
                empty_msg = f"По запросу «{query}» ничего не найдено."
            else:
                empty_msg = "Ничего не найдено."

        if self.recipes_list is not None:
            self.recipes_list.set_data(
                filtered,
                on_click=lambda r: self._on_recipe_click(r.recipe_id),
                on_right_click=lambda e, r: None,
                empty_message=empty_msg,
                prep=prep)
            if self._selected_recipe is not None:
                rid = self._selected_recipe.recipe_id
                self.recipes_list.set_selected(
                    lambda r, _rid=rid: r.recipe_id == _rid)

        self._update_skills_summary()

    def _on_recipe_click(self, recipe_id):
        recipe = next((r for r in self.recipes if r.recipe_id == recipe_id),
                      None)
        if not recipe:
            return
        self._selected_recipe = recipe

        if self.recipes_list is not None:
            self.recipes_list.set_selected(
                lambda r, _rid=recipe_id: r.recipe_id == _rid)

        available = self._is_recipe_available(recipe)
        mode = self._calc_mode

        t = self.detail_text
        t.configure(state="normal")
        t.delete("1.0", tk.END)

        product_name = self.calc.items.get(recipe.product_id,
                                           recipe.product_id)

        if not available:
            user_lvl = self._get_skill_level(recipe.skill)
            t.insert(tk.END, "  ⚠  РЕЦЕПТ НЕДОСТУПЕН\n", "bad")
            t.insert(tk.END,
                     f"  Требуется: {recipe.skill} {recipe.skill_level}   "
                     f"·   у вас: {user_lvl}\n", "warn")
            t.insert(tk.END, "  " + "─" * 76 + "\n", "muted")

        t.insert(tk.END,
                 f"  {product_name}   ×{recipe.product_count}\n", "title")
        line = f"  {recipe.station}"
        if recipe.skill and recipe.skill_level > 0:
            line += f"  ·  {recipe.skill} {recipe.skill_level}"
        elif recipe.skill:
            line += f"  ·  {recipe.skill}"

        mode_str = ("по закупочным ценам" if mode == "buy"
                    else "по себестоимости крафта")
        line += f"   ·   {mode_str}"
        t.insert(tk.END, line + "\n", "dim")
        t.insert(tk.END, "  " + "─" * 76 + "\n", "muted")

        rows = self.calc.recipe_details(recipe, mode=mode)
        total = 0.0
        unknown = 0
        for row in rows:
            t.insert(tk.END, f"  • {row['name']}  ×{row['count']}    ")
            lt = row["line_total"]
            if lt is None:
                t.insert(tk.END, "→  не рассчитать\n", "bad")
                unknown += 1
                continue

            total += lt

            if mode == "craft":
                bu = row.get("buy_unit")
                if row.get("used_craft"):
                    t.insert(tk.END,
                             f"→  🛠 крафт  {lt:>10,.0f}".replace(",", " "),
                             "craft_tag")
                    if bu is not None:
                        t.insert(tk.END,
                                 f"   (закуп {bu:,.0f})".replace(",", " "),
                                 "muted")
                    t.insert(tk.END, "\n")
                elif bu is not None:
                    t.insert(tk.END,
                             f"→  💰 закуп  {lt:>10,.0f}".replace(",", " "),
                             "ok")
                    t.insert(tk.END, "\n")
                else:
                    t.insert(tk.END, f"→  {lt:>12,.0f}\n"
                             .replace(",", " "), "ok")
            else:
                t.insert(tk.END, f"→  {lt:>12,.0f}\n"
                         .replace(",", " "), "ok")

        t.insert(tk.END, "  " + "─" * 76 + "\n", "muted")
        total_str = f"{total:>12,.0f}".replace(",", " ")
        t.insert(tk.END, f"  СЕБЕСТОИМОСТЬ:{total_str}\n", "total")
        if unknown:
            t.insert(tk.END,
                     f"  ⚠ не рассчитано {unknown} ингредиент(ов)\n",
                     "bad")
        if recipe.product_count > 0:
            per_unit = f"{total / recipe.product_count:>10,.0f}".replace(
                ",", " ")
            t.insert(tk.END, f"  Цена за единицу:{per_unit}\n", "dim")
        t.configure(state="disabled")

        pid = recipe.product_id
        saved = self.sale_prices.get(pid)
        self.sale_var.set(f"{saved:.0f}" if saved is not None else "")
        self._recalc_profit()

    def _on_sale_change(self):
        recipe = self._selected_recipe
        if recipe is None:
            return
        raw = self.sale_var.get().strip().replace(",", ".").replace(" ", "")
        if not raw:
            self.sale_prices.pop(recipe.product_id, None)
        else:
            try:
                self.sale_prices[recipe.product_id] = float(raw)
            except ValueError:
                pass
        self._recalc_profit()

    def _recalc_profit(self):
        recipe = self._selected_recipe
        if recipe is None:
            self._profit_hands.configure(text="—", text_color=C_TEXT_MUT)
            self._profit_auction.configure(text="—", text_color=C_TEXT_MUT)
            return

        raw = self.sale_var.get().strip().replace(",", ".").replace(" ", "")
        if not raw:
            self._profit_hands.configure(text="—", text_color=C_TEXT_MUT)
            self._profit_auction.configure(text="—", text_color=C_TEXT_MUT)
            return

        try:
            unit_price = float(raw)
        except ValueError:
            self._profit_hands.configure(text="не число", text_color=C_BAD)
            self._profit_auction.configure(text="не число", text_color=C_BAD)
            return

        cost = self.calc.recipe_cost(recipe, mode=self._calc_mode)
        if cost is None:
            self._profit_hands.configure(text="нет цен",
                                         text_color=C_TEXT_MUT)
            self._profit_auction.configure(text="нет цен",
                                           text_color=C_TEXT_MUT)
            return

        revenue = unit_price * recipe.product_count
        hands = revenue - cost
        auction = revenue * (1.0 - AUCTION_FEE) - cost

        def fmt(v):
            return f"{v:+,.0f} ₽".replace(",", " ")

        self._profit_hands.configure(
            text=fmt(hands), text_color=C_OK if hands >= 0 else C_BAD)
        self._profit_auction.configure(
            text=fmt(auction), text_color=C_OK if auction >= 0 else C_BAD)

    def _poll_icons(self):
        if self._ui_built:
            ready = set(self.icon_mgr.poll_ready())
            if ready:
                if self.items_list is not None:
                    for idx, item in enumerate(self.items_list.items):
                        iid, meta = item
                        url = meta.get("icon")
                        if url and url in ready:
                            photo = self._get_photo(url, meta["name"])
                            if photo is not None:
                                self.items_list.update_icon(idx, photo)
            self.after(500, self._poll_icons)

    def _reset_status(self):
        self.status_var.set(
            f"{APP_NAME} v{APP_VERSION}     "
            f"▤ {len(self.items)} предметов     "
            f"✦ {len(self.recipes)} рецептов")

    def _on_save_prices(self):
        self._save_prices()
        self._save_sale_prices()
        self._save_skills()
        self.status_var.set("Сохранено")

    def _on_reset_prices(self):
        if not self._confirm("Сбросить цены",
                             "Удалить все введённые цены?",
                             ok_text="Сбросить"):
            return
        self.calc.prices.clear()
        self._save_prices()
        self._refresh_items(force=True)
        self._refresh_recipes(force=True)
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.configure(state="disabled")
        self._selected_recipe = None
        self.sale_var.set("")
        self._recalc_profit()

    def _on_export_prices(self):
        path = filedialog.asksaveasfilename(
            title="Куда сохранить цены", defaultextension=".json",
            filetypes=[("JSON", "*.json")], initialfile="my_prices.json")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "ingredients": self.calc.prices,
                    "sale": self.sale_prices,
                }, f, ensure_ascii=False, indent=2)
            self.status_var.set("Экспортировано")
        except Exception as e:
            self._show_error("Ошибка экспорта", str(e))

    def _on_import_prices(self):
        path = filedialog.askopenfilename(
            title="Выберите файл цен", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "ingredients" in data:
                ing = data.get("ingredients") or {}
                sale = data.get("sale") or {}
            else:
                ing = data if isinstance(data, dict) else {}
                sale = {}
            for k, v in ing.items():
                self.calc.set_price(k, float(v))
            for k, v in sale.items():
                self.sale_prices[k] = float(v)
            self._save_prices()
            self._save_sale_prices()
            self._refresh_items(force=True)
            self._refresh_recipes(force=True)
            self.status_var.set(
                f"Импортировано: {len(ing)} цен, {len(sale)} продаж")
        except Exception as e:
            self._show_error("Ошибка импорта", str(e))


if __name__ == "__main__":
    app = StalzoneMain()
    app.mainloop()