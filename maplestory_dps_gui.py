# Standard Library
import os
import sys
import re
import time
import threading
import ctypes
from datetime import datetime, timedelta
from enum import Enum, auto

# GUI and Input
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
from PIL import Image, ImageTk
import keyboard
import pygetwindow as gw

# Data Processing and Science
import cv2
import mss
import numpy as np
import pandas as pd
import torch
import easyocr
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy.signal import savgol_filter
from scipy.interpolate import make_interp_spline

# Custom Modules
from languages import LANGUAGES

# System: Monkeypatch ANTIALIAS for EasyOCR compatibility with newer Pillow versions
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS


# State: Enumeration for all monitor phases
class CombatState(Enum):
    IDLE = auto()  # Not monitoring
    READY = auto()  # Monitoring but no damage yet
    ACTIVE = auto()  # Damage detected, timer running
    PAUSED = auto()  # Monitoring stopped mid-combat
    FINISHED = auto()  # Boss defeated (auto-stop)


# Mapping: Enum members to translation keys in languages.py
STATE_LANG_MAP = {
    CombatState.IDLE: "status_idle",
    CombatState.READY: "status_ready",
    CombatState.ACTIVE: "status_active",
    CombatState.PAUSED: "status_paused",
    CombatState.FINISHED: "status_finished",
}


# GUI: Enable High DPI awareness for Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# System: Load custom font from file without system installation
def load_custom_font(font_path):
    if not os.path.exists(font_path):
        return False
    FR_PRIVATE = 0x10
    path_ptr = ctypes.c_wchar_p(font_path)
    res = ctypes.windll.gdi32.AddFontResourceExW(path_ptr, FR_PRIVATE, 0)
    return res > 0


# Build: Asset path resolution and dynamic DLL loading for PyTorch
en_font_fn = "GoogleSans-VariableFont_GRAD,opsz,wght.ttf"

if getattr(sys, "frozen", False):
    bundle_dir = sys._MEIPASS
    load_custom_font(os.path.join(bundle_dir, en_font_fn))
    paths_to_add = [
        os.path.join(bundle_dir, "_internal", "torch", "lib"),
        os.path.join(bundle_dir, "_internal"),
        os.path.join(bundle_dir, "_internal", "cv2"),
    ]
    for p in paths_to_add:
        if os.path.exists(p):
            try:
                os.add_dll_directory(p)
            except:
                pass
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]
else:
    load_custom_font(en_font_fn)

# Dependencies: Patch torch.load to maintain weights_only compatibility
_original_torch_load = torch.load


def _patched_torch_load(*args, **kwargs):
    if "weights_only" in kwargs:
        del kwargs["weights_only"]
    return _original_torch_load(*args, **kwargs)


torch.load = _patched_torch_load


# UI: Color logic for HUD DPM tiers
def get_dpm_color(val):
    if val < 2000000:
        return "#FFFFEE"
    if val < 4000000:
        return "#FFFFFF"
    if val < 6000000:
        return "#FFCC00"
    if val < 8000000:
        return "#66CCFF"
    if val < 10000000:
        return "#FF80FF"
    if val < 12000000:
        return "#FFFF66"
    if val < 14000000:
        return "#66FF00"
    if val < 16000000:
        return "#FF66CC"
    return "#FF66CC"


# Region Selector: Fullscreen capture overlay
class RegionSelector(tk.Toplevel):
    def __init__(self, parent, screenshot):
        super().__init__(parent)
        self.title("Select HP Bar Region")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.canvas = tk.Canvas(self, cursor="cross", bg="grey")
        self.canvas.pack(fill="both", expand=True)
        self.img = ImageTk.PhotoImage(screenshot)
        self.canvas.create_image(0, 0, anchor="nw", image=self.img)
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.selection = None
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, 1, 1, outline="red", width=2
        )

    def on_move_press(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        x1, x2 = min(self.start_x, event.x), max(self.start_x, event.x)
        y1, y2 = min(self.start_y, event.y), max(self.start_y, event.y)
        self.selection = (x1, y1, x2 - x1, y2 - y1)
        self.destroy()


# HUD Overlay: Transparent in-game metric display
class HUDOverlay(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("MapleStory Boss HUD")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.apply_borderless_obs_style()
        self.configure(bg="black")
        self.scale_factor = 0.8
        self.opacity_val = 0.85
        self.attributes("-alpha", self.opacity_val)
        self.lang = "en"  # Default
        self.font_name = "Noto Sans TC" if self.lang == "zh" else "Google Sans"
        try:
            test_font = tkfont.Font(family=self.font_name)
            if test_font.actual()["family"] != self.font_name:
                self.font_name = "Segoe UI"
        except:
            self.font_name = "Segoe UI"

        # Controls: Hover-activated settings
        self.trans_slider = tk.Scale(
            self,
            from_=100,
            to=10,
            orient="vertical",
            bg="#222",
            fg="white",
            troughcolor="#444",
            highlightthickness=0,
            command=self.change_opacity,
            showvalue=0,
            width=15,
        )
        self.scale_slider = tk.Scale(
            self,
            from_=3.0,
            to=0.3,
            resolution=0.1,
            orient="vertical",
            bg="#222",
            fg="white",
            troughcolor="#444",
            highlightthickness=0,
            showvalue=0,
            width=15,
        )
        self.scale_slider.bind(
            "<ButtonRelease-1>", lambda e: self.change_scale(self.scale_slider.get())
        )
        self.trans_slider.set(85)
        self.scale_slider.set(0.8)

        # Layout: Grid container
        self.container = tk.Frame(self, bg="black")
        self.container.pack(padx=5, pady=(12, 5))

        self.setup_widgets()
        self.update_layout()
        self._drag_data = {"x": 0, "y": 0}
        self.bind_drag(self.container)
        self.bind("<Enter>", self.show_controls)
        self.bind("<Leave>", self.hide_controls)
        self.update_idletasks()
        self.withdraw()

    # System: Win32 API for borderless transparency
    def apply_borderless_obs_style(self):
        if sys.platform == "win32":
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.SetWindowLongW(
                hwnd,
                -16,
                ctypes.windll.user32.GetWindowLongW(hwnd, -16)
                & ~0x00C00000
                & ~0x00040000,
            )
            ctypes.windll.user32.SetWindowLongW(
                hwnd, -20, ctypes.windll.user32.GetWindowLongW(hwnd, -20) | 0x00040000
            )
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)

    # UI: Recursive binding for dragging
    def bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self.start_move)
        widget.bind("<ButtonRelease-1>", self.stop_move)
        widget.bind("<B1-Motion>", self.do_move)
        for child in widget.winfo_children():
            self.bind_drag(child)

    # UI: Label and value initialization
    def setup_widgets(self):
        self.labels = {}
        self.values = {}
        l_s = {"bg": "black", "fg": "#BBBBBB", "anchor": "center"}
        v_s = {"bg": "black", "fg": "white", "anchor": "center"}
        keys = ["time", "dps", "dmg", "rem", "dpm", "stat"]
        v = LANGUAGES[self.lang]
        txts = [
            v["hud_combat_time"],
            v["hud_rt_dps"],
            v["hud_total_dmg"],
            v["hud_remaining"],
            v["hud_avg_dpm"],
            v["hud_status"],
        ]
        for k, t in zip(keys, txts):
            self.labels[k] = tk.Label(self.container, text=t, **l_s)
            initial_val = "0"
            if k == "stat":
                initial_val = v["status_idle"]
            if k == "rem":
                initial_val = "--:--"
            if k == "time":
                initial_val = "00:00"
            self.values[k] = tk.Label(self.container, text=initial_val, **v_s)
            if k == "stat":
                self.values[k].config(fg="#00FF00")

    # UI: Multi-language layout normalization
    def update_layout(self):
        s = self.scale_factor
        f_lbl = (self.font_name, int(12 * s), "bold")
        f_val = (self.font_name, int(22 * s), "bold")
        for i in range(3):
            self.container.columnconfigure(i, weight=1, minsize=int(320 * s))

        # Spacing Normalization: Internal Padding (ipady) to match physical footprints
        # EN (Google Sans): L=57px, V=102px
        # ZH (Noto Sans TC): L=36px, V=64px
        # Inflation required for ZH: L=+21px (ipady=10.5), V=+38px (ipady=19)
        l_ipady = 10.5 if self.lang == "zh" else 0
        v_ipady = 19 if self.lang == "zh" else 0
        row_gap = int(5 * s)

        self.labels["time"].grid(row=0, column=0, ipady=l_ipady, sticky="nsew")
        self.labels["dps"].grid(row=0, column=1, ipady=l_ipady, sticky="nsew")
        self.labels["dmg"].grid(row=0, column=2, ipady=l_ipady, sticky="nsew")

        self.values["time"].grid(
            row=1, column=0, ipady=v_ipady, pady=(0, row_gap), sticky="nsew"
        )
        self.values["dps"].grid(
            row=1, column=1, ipady=v_ipady, pady=(0, row_gap), sticky="nsew"
        )
        self.values["dmg"].grid(
            row=1, column=2, ipady=v_ipady, pady=(0, row_gap), sticky="nsew"
        )

        self.labels["rem"].grid(row=2, column=0, ipady=l_ipady, sticky="nsew")
        self.labels["dpm"].grid(row=2, column=1, ipady=l_ipady, sticky="nsew")
        self.labels["stat"].grid(row=2, column=2, ipady=l_ipady, sticky="nsew")

        self.values["rem"].grid(row=3, column=0, ipady=v_ipady, sticky="nsew")
        self.values["dpm"].grid(row=3, column=1, ipady=v_ipady, sticky="nsew")
        self.values["stat"].grid(row=3, column=2, ipady=v_ipady, sticky="nsew")

        for l in self.labels.values():
            l.config(font=f_lbl)
        for k, v in self.values.items():
            v.config(font=f_val if k != "stat" else f_lbl)

    def show_controls(self, event=None):
        self.trans_slider.place(x=0, y=0, relheight=1, width=15)
        self.scale_slider.place(relx=1.0, x=-15, y=0, relheight=1, width=15)

    def hide_controls(self, event=None):
        x, y = self.winfo_pointerxy()
        wx, wy = self.winfo_rootx(), self.winfo_rooty()
        ww, wh = self.winfo_width(), self.winfo_height()
        if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
            self.trans_slider.place_forget()
            self.scale_slider.place_forget()

    def change_opacity(self, val):
        self.attributes("-alpha", float(val) / 100.0)

    def change_scale(self, val):
        self.scale_factor = float(val)
        self.update_layout()

    # UI: Hot-swap HUD font and labels
    def update_language(self, lang):
        self.lang = lang
        self.font_name = "Noto Sans TC" if self.lang == "zh" else "Google Sans"
        v = LANGUAGES[self.lang]
        self.labels["time"].config(text=v["hud_combat_time"])
        self.labels["dps"].config(text=v["hud_rt_dps"])
        self.labels["dmg"].config(text=v["hud_total_dmg"])
        self.labels["rem"].config(text=v["hud_remaining"])
        self.labels["dpm"].config(text=v["hud_avg_dpm"])
        self.labels["stat"].config(text=v["hud_status"])
        self.update_layout()

    def start_move(self, event):
        self._drag_data["x"] = event.x_root - self.winfo_x()
        self._drag_data["y"] = event.y_root - self.winfo_y()

    def stop_move(self, event):
        pass

    def do_move(self, event):
        nx = event.x_root - self._drag_data["x"]
        ny = event.y_root - self._drag_data["y"]
        self.geometry(f"+{nx}+{ny}")

    # UI: Push real-time metrics to HUD
    def update_metrics(self, combat_time, dps, dpm, total_dmg, state, rem_time):
        self.values["time"].config(text=combat_time)
        self.values["dps"].config(text=f"{dps:,.0f}")
        self.values["dmg"].config(text=f"{total_dmg:,.0f}")
        self.values["rem"].config(text=rem_time)
        self.values["dpm"].config(text=f"{dpm:,.0f}", fg=get_dpm_color(dpm))

        v = LANGUAGES[self.lang]
        st_text = v[STATE_LANG_MAP[state]].upper()
        self.values["stat"].config(text=st_text)

        if state == CombatState.ACTIVE:
            self.values["stat"].config(fg="#FF4444")
        elif state == CombatState.FINISHED:
            self.values["stat"].config(fg="#FFD700")
        elif state == CombatState.READY:
            self.values["stat"].config(fg="#66CCFF")
        else:
            self.values["stat"].config(fg="#00FF00")


# Main Dashboard: System orchestration and analytics GUI
class BossDPSMonitorGUI:
    def __init__(self, root):
        self.root = root

        # System: DPI and scaling awareness
        try:
            from ctypes import wintypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            h_mon = ctypes.windll.user32.MonitorFromPoint(wintypes.POINT(0, 0), 1)
            scale_val = ctypes.c_uint()
            ctypes.windll.shcore.GetScaleFactorForMonitor(
                h_mon, ctypes.byref(scale_val)
            )
            current_scaling = scale_val.value / 100.0
        except:
            current_scaling = self.root.winfo_fpixels("1i") / 72.0

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # UI: 4K Master Reference Ratio
        REF_W, REF_H, REF_SCALE = 3840.0, 2160.0, 1.75
        logical_h = screen_h / current_scaling
        ref_logical_h = REF_H / REF_SCALE
        self.ui_scale = logical_h / ref_logical_h

        win_w = int(screen_w * (650.0 / REF_W))
        win_h = int(min(screen_h * (1500.0 / REF_H), screen_h * 0.9))

        # Vars: Global state and localization
        self.lang = "en"
        v = LANGUAGES[self.lang]
        self.root.title(v["title"] + f" v20260403.8")
        self.root.geometry(f"{win_w}x{win_h}")

        self.font_name = "Noto Sans TC" if self.lang == "zh" else "Google Sans"
        try:
            test_font = tkfont.Font(family=self.font_name)
            if test_font.actual()["family"] != self.font_name:
                self.font_name = "Segoe UI"
        except:
            self.font_name = "Segoe UI"

        self.font_large = (self.font_name, int(16 * self.ui_scale), "bold")
        self.font_medium = (self.font_name, int(12 * self.ui_scale))
        self.font_small = (self.font_name, int(10 * self.ui_scale))

        # UI Styling: Style refresh hook
        self.style = ttk.Style()
        self.style.configure(".", font=(self.font_name, int(10 * self.ui_scale)))

        # State: Data tracking
        self.hp_history = []
        self.total_damage = 0
        self.initial_hp = None
        self.accumulated_combat_time = 0.0
        self.fight_session_start = None
        self.last_detected_hp = None
        self.last_hp_seen_time = 0
        self.rt_start_idx = 0
        self.capture_region = None
        self.use_gpu = torch.cuda.is_available()
        self.gpu_name = torch.cuda.get_device_name(0) if self.use_gpu else "CPU Mode"
        self.current_state = CombatState.IDLE
        self.engine_ready = False

        # Vars: UI binding
        self.hp_val_var = tk.StringVar(value="-")
        self.rt_dps_val_var = tk.StringVar(value="-")
        self.rt_dpm_val_var = tk.StringVar(value="-")
        self.combat_time_val_var = tk.StringVar(value="00:00")
        self.total_dmg_val_var = tk.StringVar(value="-")
        self.avg_dpm_val_var = tk.StringVar(value="-")
        self.rem_time_val_var = tk.StringVar(value="--:--")
        self.status_var = tk.StringVar(value=v["engine_loading"])
        self.monitor_status_var = tk.StringVar(value=v["monitoring_off"])
        self.combat_status_var = tk.StringVar(
            value=f"{'戰鬥狀態' if self.lang=='zh' else 'Combat'}: {v['status_idle']}"
        )
        self.perf_var = tk.StringVar(value="Actual Hz: -")

        self.setup_ui()
        self.reader = None
        threading.Thread(target=self.init_ocr, daemon=True).start()
        self.hud = HUDOverlay(self.root)
        self.hud.update_language(self.lang)
        self.setup_hotkeys()

    # UI: Build control panel layout
    def setup_ui(self):
        # UI: Persistent status bar
        self.stat_container = ttk.Frame(self.root)
        self.stat_container.pack(side="bottom", fill="x", padx=10, pady=(0, 2))
        self.stat_container.columnconfigure(2, weight=1)

        st_f = (self.font_name, int(9 * self.ui_scale))
        st_bf = (self.font_name, int(9 * self.ui_scale), "bold")

        self.engine_lbl = ttk.Label(
            self.stat_container, textvariable=self.status_var, font=st_f
        )
        self.engine_lbl.grid(row=0, column=0, sticky="w")
        self.hw_lbl = ttk.Label(
            self.stat_container,
            text=f"| {LANGUAGES[self.lang]['hw_label']} {self.gpu_name}",
            font=st_f,
        )
        self.hw_lbl.grid(row=0, column=1, sticky="w", padx=10)
        self.perf_lbl = ttk.Label(
            self.stat_container, textvariable=self.perf_var, font=st_f
        )
        self.perf_lbl.grid(row=0, column=2, sticky="e")

        self.monitor_lbl = ttk.Label(
            self.stat_container,
            textvariable=self.monitor_status_var,
            font=st_bf,
            foreground="#1976d2",
        )
        self.monitor_lbl.grid(row=1, column=0, columnspan=2, sticky="w")
        self.combat_lbl = ttk.Label(
            self.stat_container,
            textvariable=self.combat_status_var,
            font=st_bf,
            foreground="#FF4444",
        )
        self.combat_lbl.grid(row=1, column=2, sticky="e")

        # UI: Scrollable main container
        self.main_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self.root, orient="vertical", command=self.main_canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            ),
        )
        self.canvas_window = self.main_canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.main_canvas.bind("<Configure>", self._on_canvas_configure)
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="top", fill="both", expand=True)
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        content = self.scrollable_frame
        pad_val = int(30 * self.ui_scale)
        inner_pad = int(12 * self.ui_scale)
        pad = {"padx": pad_val, "pady": inner_pad}

        # UI: Config Frame
        self.settings_f = ttk.LabelFrame(
            content, text=LANGUAGES[self.lang]["config_frame"]
        )
        self.settings_f.pack(fill="x", **pad)

        lang_f = ttk.Frame(self.settings_f)
        lang_f.pack(fill="x", padx=10, pady=2)
        ttk.Label(lang_f, text="Language / 語言:").pack(side="left", padx=5)
        self.lang_list = ttk.Combobox(
            lang_f, values=["English", "繁體中文"], state="readonly", width=15
        )
        self.lang_list.set("繁體中文" if self.lang == "zh" else "English")
        self.lang_list.pack(side="left", padx=5)
        self.lang_list.bind("<<ComboboxSelected>>", self.on_lang_change)

        self.win_list_lbl = ttk.Label(
            self.settings_f, text=LANGUAGES[self.lang]["window_list_label"]
        )
        self.win_list_lbl.pack(padx=10, pady=(5, 0), anchor="w")
        self.window_list = ttk.Combobox(self.settings_f, width=int(50 * self.ui_scale))
        self.window_list.pack(padx=10, pady=5)
        self.window_list.bind("<<ComboboxSelected>>", self.on_window_change)

        btn_f = ttk.Frame(self.settings_f)
        btn_f.pack(fill="x", padx=10, pady=5)
        self.refresh_btn = ttk.Button(
            btn_f,
            text=LANGUAGES[self.lang]["refresh_btn"],
            command=self.refresh_windows,
        )
        self.refresh_btn.pack(side="left", fill="x", expand=True, padx=5)
        self.set_region_btn = ttk.Button(
            btn_f, text=LANGUAGES[self.lang]["set_region_btn"], command=self.set_region
        )
        self.set_region_btn.pack(side="left", fill="x", expand=True, padx=5)

        self.region_display = tk.Label(
            self.settings_f,
            text=LANGUAGES[self.lang]["region_not_set"],
            font=(self.font_name, int(9 * self.ui_scale), "bold"),
            fg="#C62828",
            bg="#FFEBEE",
            padx=12,
            pady=4,
        )
        self.region_display.pack(pady=8)

        freq_f = ttk.Frame(self.settings_f)
        freq_f.pack(fill="x", pady=5)
        self.freq_lbl = ttk.Label(freq_f, text=LANGUAGES[self.lang]["freq_label"])
        self.freq_lbl.pack(side="left", padx=10)
        self.freq_var = tk.IntVar(value=2)
        self.freq_scale = ttk.Scale(
            freq_f,
            from_=1,
            to=10,
            variable=self.freq_var,
            orient="horizontal",
            command=lambda v: self.freq_var.set(int(float(v))),
        )
        self.freq_scale.pack(side="left", fill="x", expand=True, padx=10)
        ttk.Label(freq_f, textvariable=self.freq_var, width=4).pack(side="left")
        self.hint_lbl = ttk.Label(
            self.settings_f,
            text=LANGUAGES[self.lang]["hotkey_hint"],
            font=(self.font_name, int(10 * self.ui_scale)),
            foreground="gray",
        )
        self.hint_lbl.pack(pady=2)

        # UI: Dashboard Frame
        self.dash_f = ttk.LabelFrame(
            content, text=LANGUAGES[self.lang]["dashboard_frame"]
        )
        self.dash_f.pack(fill="x", **pad)

        self.metrics_container = ttk.Frame(self.dash_f)
        self.metrics_container.pack(
            fill="x", padx=int(40 * self.ui_scale), pady=int(15 * self.ui_scale)
        )
        self.metrics_container.columnconfigure(1, weight=1)
        self.refresh_dashboard_labels()

        report_btn_f = ttk.Frame(content)
        report_btn_f.pack(padx=pad_val, pady=5, fill="x")
        self.gen_report_btn = ttk.Button(
            report_btn_f,
            text=LANGUAGES[self.lang]["gen_report_btn"],
            command=self.generate_report,
        )
        self.gen_report_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.export_csv_btn = ttk.Button(
            report_btn_f,
            text=LANGUAGES[self.lang]["export_csv_btn"],
            command=self.export_raw_data,
        )
        self.export_csv_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

        self.refresh_windows()

    # UI: Instant language and font hot-swap
    def on_lang_change(self, event=None):
        selection = self.lang_list.get()
        self.lang = "zh" if selection == "繁體中文" else "en"
        v = LANGUAGES[self.lang]

        # Typography: Update families based on selection
        self.font_name = "Noto Sans TC" if self.lang == "zh" else "Google Sans"
        self.font_large = (self.font_name, int(16 * self.ui_scale), "bold")
        self.font_medium = (self.font_name, int(12 * self.ui_scale))
        self.font_small = (self.font_name, int(10 * self.ui_scale))

        style = ttk.Style()
        st_f = (self.font_name, int(10 * self.ui_scale))
        st_bf = (self.font_name, int(11 * self.ui_scale), "bold")
        style.configure(".", font=st_f)
        style.configure("TLabel", font=st_f)
        style.configure("TLabelframe.Label", font=st_bf)
        style.configure("TButton", font=st_f)
        style.configure("TCombobox", font=st_f)

        # UI: Title and Frame labels
        self.root.title(v["title"] + f" v20260403.8")
        self.settings_f.config(text=v["config_frame"])
        self.dash_f.config(text=v["dashboard_frame"])

        # UI: Interactive buttons and labels
        self.win_list_lbl.config(text=v["window_list_label"])
        self.refresh_btn.config(text=v["refresh_btn"])
        self.set_region_btn.config(text=v["set_region_btn"])
        self.freq_lbl.config(text=v["freq_label"])
        self.hint_lbl.config(
            text=v["hotkey_hint"], font=(self.font_name, int(10 * self.ui_scale))
        )
        self.gen_report_btn.config(text=v["gen_report_btn"])
        self.export_csv_btn.config(text=v["export_csv_btn"])

        # UI: Region status pill font update
        st_bf_region = (self.font_name, int(9 * self.ui_scale), "bold")
        if self.capture_region:
            self.region_display.config(text=v["region_set"], font=st_bf_region)
        else:
            self.region_display.config(text=v["region_not_set"], font=st_bf_region)

        # UI: Status Bar normalization and font refresh
        st_v_off = int(9.5 * self.ui_scale) if self.lang == "zh" else 0
        st_f = (self.font_name, int(9 * self.ui_scale))
        st_bf = (self.font_name, int(9 * self.ui_scale), "bold")

        self.engine_lbl.config(font=st_f)
        self.engine_lbl.grid_configure(pady=(st_v_off, 0))
        self.hw_lbl.config(text=f"| {v['hw_label']} {self.gpu_name}", font=st_f)
        self.hw_lbl.grid_configure(pady=(st_v_off, 0))
        self.perf_lbl.config(font=st_f)
        self.perf_lbl.grid_configure(pady=(st_v_off, 0))
        self.monitor_lbl.config(font=st_bf)
        self.monitor_lbl.grid_configure(pady=(0, st_v_off))
        self.combat_lbl.config(font=st_bf)
        self.combat_lbl.grid_configure(pady=(0, st_v_off))

        # State: Re-fetch localized status strings
        self.status_var.set(
            v["engine_ready"] if self.engine_ready else v["engine_loading"]
        )
        m_st = (
            v["monitoring_on"]
            if self.current_state in [CombatState.READY, CombatState.ACTIVE]
            else v["monitoring_off"]
        )
        self.monitor_status_var.set(m_st)

        prefix = "戰鬥狀態" if self.lang == "zh" else "Combat"
        translated_st = v[STATE_LANG_MAP[self.current_state]]
        self.combat_status_var.set(f"{prefix}: {translated_st}")

        # Final UI synchronization
        self.hud.update_language(self.lang)
        self.refresh_dashboard_labels()
        self.refresh_metrics_display(
            self.last_detected_hp or 0, time.time(), self.current_state
        )

    # UI: Metric list generation with additive padding
    def refresh_dashboard_labels(self):
        for child in self.metrics_container.winfo_children():
            child.destroy()

        v = LANGUAGES[self.lang]
        # Layout: Pixel-perfect padding normalization
        base_pady = 8 * self.ui_scale
        if self.lang == "zh":
            row_pady = int(base_pady + (17.5 * self.ui_scale))
            sep_pady = int(15 * self.ui_scale + (10 * self.ui_scale))
        else:
            row_pady = int(base_pady)
            sep_pady = int(15 * self.ui_scale)

        m_config = [
            (v["hp_label"], self.hp_val_var, "red"),
            (v["rt_dps_label"], self.rt_dps_val_var, None),
            (v["rt_dpm_label"], self.rt_dpm_val_var, None),
            ("SEP", None, None),
            (v["combat_time_label"], self.combat_time_val_var, None),
            (v["rem_time_label"], self.rem_time_val_var, "#673ab7"),
            (v["total_dmg_label"], self.total_dmg_val_var, "#388e3c"),
            (v["avg_dpm_label"], self.avg_dpm_val_var, "#1976d2"),
        ]

        row_idx = 0
        for name, var, color in m_config:
            if name == "SEP":
                ttk.Separator(self.metrics_container, orient="horizontal").grid(
                    row=row_idx, column=0, columnspan=2, sticky="ew", pady=sep_pady
                )
                row_idx += 1
                continue
            lbl = ttk.Label(
                self.metrics_container, text=f"{name}:", font=self.font_large
            )
            val = ttk.Label(
                self.metrics_container, textvariable=var, font=self.font_large
            )
            if color:
                val.config(foreground=color)
                if name == v["hp_label"]:
                    lbl.config(foreground=color)
            lbl.grid(row=row_idx, column=0, sticky="w", pady=row_pady)
            val.grid(row=row_idx, column=1, sticky="e", pady=row_pady)
            row_idx += 1

    def _on_canvas_configure(self, event):
        self.main_canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_window_change(self, event=None):
        self.capture_region = None
        v = LANGUAGES[self.lang]
        self.region_display.config(text=v["region_not_set"], fg="#C62828", bg="#FFEBEE")

    # System: Engine initialization
    def init_ocr(self):
        try:
            self.reader = easyocr.Reader(["en"], gpu=self.use_gpu)
            self.engine_ready = True
            v = LANGUAGES[self.lang]
            self.status_var.set(v["engine_ready"])
        except Exception as e:
            self.status_var.set(f"OCR Error: {str(e)[:20]}")

    # System: Keyboard hotkeys
    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey("f7", self.hotkey_toggle)
            keyboard.add_hotkey("f8", self.hotkey_reset)
            keyboard.add_hotkey("f9", self.hotkey_hud)
        except Exception:
            pass

    def hotkey_toggle(self):
        self.root.after(0, self.toggle_monitoring)

    def hotkey_reset(self):
        self.root.after(0, self.reset_metrics)

    def hotkey_hud(self):
        self.root.after(0, self.toggle_hud)

    def toggle_hud(self):
        if self.hud.winfo_viewable():
            self.hud.withdraw()
        else:
            self.hud.deiconify()

    def refresh_windows(self):
        titles = [w for w in gw.getAllTitles() if w.strip()]
        self.window_list["values"] = titles
        if titles:
            self.window_list.current(0)

    # UI: HP bar crop selection tool
    def set_region(self):
        selection = self.window_list.get()
        windows = gw.getWindowsWithTitle(selection)
        if not windows:
            return
        win = windows[0]
        with mss.mss() as sct:
            monitor = {
                "top": win.top,
                "left": win.left,
                "width": win.width,
                "height": win.height,
            }
            sct_img = sct.grab(monitor)
            screenshot = Image.frombytes(
                "RGB", sct_img.size, sct_img.bgra, "raw", "BGRX"
            )
            selector = RegionSelector(self.root, screenshot)
            self.root.wait_window(selector)
            if selector.selection:
                self.capture_region = selector.selection
                v = LANGUAGES[self.lang]
                self.region_display.config(
                    text=v["region_set"], fg="#2E7D32", bg="#E8F5E9"
                )

    # UI: Centralized data push to Dashboard and HUD
    def refresh_metrics_display(self, current_hp, now, state):
        target_hz = self.freq_var.get()
        interval = 1.0 / target_hz
        total_time = self.accumulated_combat_time
        if state == CombatState.ACTIVE and self.fight_session_start:
            total_time += now - self.fight_session_start

        rt_dps, avg_dpm = 0, 0
        rem_t_str = self.rem_time_val_var.get()

        if total_time > 0:
            if state == CombatState.ACTIVE and self.fight_session_start:
                lookback_idx = max(
                    self.rt_start_idx, len(self.hp_history) - int(3 * target_hz) - 1
                )
                if len(self.hp_history) > lookback_idx:
                    dt_recent = now - self.hp_history[lookback_idx][0]
                    if dt_recent > 0:
                        rt_dps = max(
                            0,
                            (self.hp_history[lookback_idx][1] - current_hp) / dt_recent,
                        )
            avg_dpm = (self.total_damage / max(interval, total_time)) * 60
            if avg_dpm > 0:
                rem_t_str = self.format_combat_time(current_hp / (avg_dpm / 60), True)
            else:
                rem_t_str = "--:--"

        self.rt_dps_val_var.set(f"{rt_dps:,.0f}")
        self.rt_dpm_val_var.set(f"{rt_dps * 60:,.0f}")
        self.combat_time_val_var.set(self.format_combat_time(total_time, short=True))
        self.total_dmg_val_var.set(f"{self.total_damage:,}")
        self.avg_dpm_val_var.set(f"{avg_dpm:,.0f}")
        self.rem_time_val_var.set(rem_t_str)
        self.hp_val_var.set(f"{current_hp:,}" if current_hp > 0 else "0")

        self.hud.update_metrics(
            self.format_combat_time(total_time, short=True),
            rt_dps,
            avg_dpm,
            self.total_damage,
            state,
            rem_t_str,
        )

    # State: Monitoring lifecycle management
    def toggle_monitoring(self):
        now = time.time()
        v = LANGUAGES[self.lang]
        prefix = "戰鬥狀態" if self.lang == "zh" else "Combat"

        if self.current_state != CombatState.IDLE:
            if self.current_state == CombatState.ACTIVE and self.fight_session_start:
                self.accumulated_combat_time += now - self.fight_session_start
            self.current_state = (
                CombatState.PAUSED if self.total_damage > 0 else CombatState.IDLE
            )
            self.monitor_status_var.set(v["monitoring_off"])
            translated_st = v[STATE_LANG_MAP[self.current_state]]
            self.combat_status_var.set(f"{prefix}: {translated_st}")
            self.refresh_metrics_display(
                self.last_detected_hp or 0, now, self.current_state
            )
        else:
            if not self.reader:
                return
            selection = self.window_list.get()
            windows = gw.getWindowsWithTitle(selection)
            if not windows:
                return
            self.target_window = windows[0]
            self.current_state = CombatState.READY
            self.fight_session_start = None
            self.monitor_status_var.set(v["monitoring_on"])
            translated_st = v[STATE_LANG_MAP[self.current_state]]
            self.combat_status_var.set(f"{prefix}: {translated_st}")
            self.refresh_metrics_display(
                self.last_detected_hp or 0, now, self.current_state
            )
            threading.Thread(target=self.monitor_loop, daemon=True).start()

    # State: Wipe data session
    def reset_metrics(self):
        v = LANGUAGES[self.lang]
        prefix = "戰鬥狀態" if self.lang == "zh" else "Combat"
        self.hp_history, self.total_damage, self.initial_hp = [], 0, None
        self.accumulated_combat_time, self.fight_session_start = 0.0, None
        is_mon = self.current_state in [
            CombatState.READY,
            CombatState.ACTIVE,
            CombatState.PAUSED,
            CombatState.FINISHED,
        ]
        self.current_state = CombatState.READY if is_mon else CombatState.IDLE
        self.last_detected_hp, self.last_hp_seen_time = None, 0
        self.hp_val_var.set("-")
        self.rt_dps_val_var.set("-")
        self.rt_dpm_val_var.set("-")
        self.combat_time_val_var.set("00:00")
        self.total_dmg_val_var.set("-")
        self.avg_dpm_val_var.set("-")
        self.rem_time_val_var.set("--:--")
        st_text = v[STATE_LANG_MAP[self.current_state]]
        self.combat_status_var.set(f"{prefix}: {st_text}")
        self.refresh_metrics_display(0, time.time(), self.current_state)

    # UI: Time string generation
    def format_combat_time(self, seconds, short=False):
        td = timedelta(seconds=int(max(0, seconds)))
        parts = str(td).split(":")
        return (
            f"{int(parts[1]):02d}:{int(parts[2]):02d}"
            if short
            else f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
        )

    # Engine: Background monitoring thread
    def monitor_loop(self):
        with mss.mss() as sct:
            while self.current_state in [CombatState.READY, CombatState.ACTIVE]:
                loop_start = time.time()
                win = self.target_window
                if win.isMinimized or not win.visible:
                    time.sleep(1.0 / self.freq_var.get())
                    continue
                monitor = (
                    {
                        "top": win.top + self.capture_region[1],
                        "left": win.left + self.capture_region[0],
                        "width": self.capture_region[2],
                        "height": self.capture_region[3],
                    }
                    if self.capture_region
                    else {
                        "top": win.top,
                        "left": win.left,
                        "width": win.width,
                        "height": int(win.height * 0.35),
                    }
                )
                img_raw = np.array(sct.grab(monitor))
                img_processed = cv2.cvtColor(img_raw, cv2.COLOR_BGRA2GRAY)
                results = []
                try:
                    results = self.reader.readtext(img_processed, detail=0)
                except:
                    pass

                current_hp, now = None, time.time()
                if results:
                    full_text = " ".join(results)
                    matches = re.findall(r"(\d{1,3}(?:,\d{3})*)", full_text)
                    valid = [
                        int(m.replace(",", ""))
                        for m in matches
                        if 100 < int(m.replace(",", "")) < 10**15
                    ]
                    hp = max(valid) if valid else None
                    if hp and not self.is_outlier(hp, now):
                        current_hp = hp

                if current_hp:
                    v, prefix = LANGUAGES[self.lang], (
                        "戰鬥狀態" if self.lang == "zh" else "Combat"
                    )
                    if self.last_detected_hp is None:
                        self.last_detected_hp, self.last_hp_seen_time = current_hp, now
                    if (
                        self.current_state == CombatState.READY
                        and current_hp < self.last_detected_hp
                    ):
                        self.current_state, self.fight_session_start, self.rt_start_idx = (
                            CombatState.ACTIVE,
                            now,
                            0,
                        )
                        self.initial_hp = self.initial_hp or self.last_detected_hp
                        self.combat_status_var.set(f"{prefix}: {v['status_active']}")
                    if self.current_state == CombatState.ACTIVE:
                        self.hp_history.append((now, current_hp))
                        self.total_damage = max(0, self.initial_hp - current_hp)
                    else:
                        self.hp_history, self.rt_start_idx = [(now, current_hp)], 0
                    self.refresh_metrics_display(current_hp, now, self.current_state)
                    self.last_detected_hp, self.last_hp_seen_time = current_hp, now
                elif (
                    self.current_state == CombatState.ACTIVE
                    and now - self.last_hp_seen_time >= 1.0
                    and self.last_detected_hp < 500000
                ):
                    self.finalize_combat(now, 1.0 / self.freq_var.get())

                elapsed = time.time() - loop_start
                self.perf_var.set(f"Actual Hz: {1.0/max(0.001, elapsed):.1f}")
                time.sleep(max(0, (1.0 / self.freq_var.get()) - elapsed))

    # Engine: End of combat logic
    def finalize_combat(self, now, interval):
        v, prefix = LANGUAGES[self.lang], ("戰鬥狀態" if self.lang == "zh" else "Combat")
        self.current_state = CombatState.FINISHED
        f_ts = self.last_hp_seen_time + interval
        if self.fight_session_start:
            self.accumulated_combat_time += f_ts - self.fight_session_start
        self.fight_session_start = None
        self.total_damage = self.initial_hp or self.total_damage
        self.combat_status_var.set(f"{prefix}: {v['status_finished']}")
        self.monitor_status_var.set(v["monitoring_off"])
        self.refresh_metrics_display(0, now, self.current_state)

    def is_outlier(self, hp, now):
        if self.last_detected_hp is None:
            return False
        return hp > self.last_detected_hp + 50000 or hp < self.last_detected_hp - 2000000

    # Analytics: PNG report generation
    def generate_report(self):
        v = LANGUAGES[self.lang]
        if not self.hp_history:
            messagebox.showwarning(v["warning_msg"], v["no_data_msg"])
            return
        try:
            df_raw = pd.DataFrame(self.hp_history, columns=["Timestamp", "HP"]).drop_duplicates(subset=["Timestamp"])
            df_raw["TimeSec"] = df_raw["Timestamp"] - df_raw["Timestamp"].iloc[0]
            df_raw["RT_DPS"] = ((df_raw["HP"].shift(1) - df_raw["HP"]) / df_raw["Timestamp"].diff()).fillna(0)
            df_raw = df_raw.replace([np.inf, -np.inf], np.nan).dropna(subset=["RT_DPS"])
            df_raw = df_raw[df_raw["RT_DPS"] >= 0]
            if len(df_raw) < 10:
                messagebox.showwarning(v["warning_msg"], v["not_enough_data"])
                return
            window_len = min(len(df_raw) // 2, 51)
            if window_len % 2 == 0: window_len += 1
            smoothed_dps = savgol_filter(df_raw["RT_DPS"], max(5, window_len), 2)
            time_new = np.linspace(df_raw["TimeSec"].min(), df_raw["TimeSec"].max(), 500)
            interp_dps = np.clip(make_interp_spline(df_raw["TimeSec"], smoothed_dps, k=3)(time_new), 0, None)
            sns.set_theme(style="whitegrid", font=self.font_name)
            plt.figure(figsize=(12, 7))
            sns.lineplot(x=time_new, y=interp_dps, color="#1976d2", linewidth=2.5)
            plt.fill_between(time_new, interp_dps, color="#1976d2", alpha=0.15)
            total_t = self.accumulated_combat_time + (time.time() - self.fight_session_start if (self.current_state == CombatState.ACTIVE and self.fight_session_start) else 0.0)
            avg_dps = self.total_damage / max(0.1, total_t)
            plt.axhline(y=avg_dps, color="#D32F2F", linestyle="--", alpha=0.8, label=v["avg_dps_legend"])
            plt.title(v["report_title"], fontsize=18, pad=20, weight="bold")
            plt.xlabel(v["report_xlabel"], fontsize=12); plt.ylabel(v["report_ylabel"], fontsize=12)
            plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
            plt.legend(frameon=True, facecolor="white")
            summary_text = f"{v['combat_time_label']:<15} : {self.format_combat_time(total_t, short=True):>15}\n{v['total_dmg_label']:<15} : {self.total_damage:>15,}\n{v['rt_dps_label']:<15} : {avg_dps:>15,.0f}\n{v['avg_dpm_label']:<15} : {avg_dps*60:>15,.0f}"
            plt.text(0.02, 0.96, summary_text, transform=plt.gca().transAxes, verticalalignment="top", family="monospace", fontsize=11, bbox=dict(boxstyle="round,pad=1", facecolor="white", edgecolor="#DDDDDD", alpha=0.95))
            plt.tight_layout(); fname = f"Boss_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(fname, dpi=150); plt.close(); messagebox.showinfo(v["success_msg"], f"{v['report_saved']} {fname}")
        except Exception as e: messagebox.showerror("Error", str(e))

    # Analytics: Raw data export
    def export_raw_data(self):
        v = LANGUAGES[self.lang]
        if not self.hp_history:
            messagebox.showwarning(v["warning_msg"], v["no_data_msg"])
            return
        try:
            df = pd.DataFrame(self.hp_history, columns=["UnixTimestamp", "HP"])
            df["TimeSec"] = df["UnixTimestamp"] - df["UnixTimestamp"].iloc[0]
            fname = f"Combat_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(fname, index=False)
            messagebox.showinfo(v["success_msg"], f"{v['csv_exported']} {fname}")
        except Exception as e: messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = BossDPSMonitorGUI(root)
    root.mainloop()
