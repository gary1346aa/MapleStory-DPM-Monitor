import cv2
from PIL import Image, ImageTk

# System: Monkeypatch ANTIALIAS for EasyOCR compatibility with newer Pillow versions
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import easyocr
import mss
import numpy as np
import time
import re
import pygetwindow as gw
from collections import deque
import sys
import torch
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import tkinter.font as tkfont
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from scipy.signal import savgol_filter
from scipy.interpolate import make_interp_spline
from datetime import datetime, timedelta
import os
import ctypes
import keyboard

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
    # AddFontResourceEx is a Win32 API to load fonts for the current process
    FR_PRIVATE = 0x10
    path_ptr = ctypes.c_wchar_p(font_path)
    res = ctypes.windll.gdi32.AddFontResourceExW(path_ptr, FR_PRIVATE, 0)
    return res > 0

# Build: Fix for bundled PyTorch GPU support in frozen executables
if getattr(sys, "frozen", False):
    bundle_dir = sys._MEIPASS
    font_file = os.path.join(bundle_dir, "GoogleSans-VariableFont_GRAD,opsz,wght.ttf")
    load_custom_font(font_file)
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
    # Load font in dev mode
    load_custom_font("GoogleSans-VariableFont_GRAD,opsz,wght.ttf")

# Dependencies: Patch torch.load to avoid weights_only issues
_original_torch_load = torch.load


def _patched_torch_load(*args, **kwargs):
    if "weights_only" in kwargs:
        del kwargs["weights_only"]
    return _original_torch_load(*args, **kwargs)


torch.load = _patched_torch_load


# UI: Helper to determine HUD color based on DPM tiers
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


# Region Selector: Fullscreen overlay for selecting the boss HP bar
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


# HUD Overlay: Transparent, OBS-friendly window for in-game monitoring
class HUDOverlay(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("MapleStory Boss HUD")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.apply_borderless_obs_style()
        self.configure(bg="black")
        self.scale_factor = 1.0
        self.opacity_val = 0.85
        self.attributes("-alpha", self.opacity_val)
        self.font_name = "Google Sans"
        try:
            test_font = tkfont.Font(family=self.font_name)
            if test_font.actual()["family"] != self.font_name:
                self.font_name = "Segoe UI"
        except:
            self.font_name = "Segoe UI"

        # Controls: Hover-activated transparency and scale sliders
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
        self.scale_slider.set(1.0)

        # Layout: Main container with padding for drag handle
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

    # System: Win32 API calls to make borderless window capturable by OBS
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

    # UI: Recursive binding for jitter-free dragging
    def bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self.start_move)
        widget.bind("<ButtonRelease-1>", self.stop_move)
        widget.bind("<B1-Motion>", self.do_move)
        for child in widget.winfo_children():
            self.bind_drag(child)

    # UI: Initialization of labels and value displays
    def setup_widgets(self):
        self.labels = {}
        self.values = {}
        l_s = {"bg": "black", "fg": "#BBBBBB", "anchor": "center"}
        v_s = {"bg": "black", "fg": "white", "anchor": "center"}
        keys = ["time", "dps", "dmg", "rem", "dpm", "stat"]
        txts = [
            "COMBAT TIME",
            "REAL-TIME DPS",
            "TOTAL DAMAGE",
            "REMAINING",
            "AVERAGE DPM",
            "STATUS",
        ]
        for k, t in zip(keys, txts):
            self.labels[k] = tk.Label(self.container, text=t, **l_s)
            self.values[k] = tk.Label(
                self.container, text="0" if k != "stat" else "IDLE", **v_s
            )
            if k == "stat":
                self.values[k].config(fg="#00FF00")

    # UI: Symmetrical 3-column grid layout with scaling
    def update_layout(self):
        s = self.scale_factor
        f_lbl = (self.font_name, int(12 * s), "bold")
        f_val = (self.font_name, int(22 * s), "bold")
        for i in range(3):
            self.container.columnconfigure(i, weight=1, minsize=int(320 * s))
        row_p = int(5 * s)
        self.labels["time"].grid(row=0, column=0, pady=(0, 0), sticky="nsew")
        self.labels["dps"].grid(row=0, column=1, pady=(0, 0), sticky="nsew")
        self.labels["dmg"].grid(row=0, column=2, pady=(0, 0), sticky="nsew")
        self.values["time"].grid(row=1, column=0, pady=(0, row_p), sticky="nsew")
        self.values["dps"].grid(row=1, column=1, pady=(0, row_p), sticky="nsew")
        self.values["dmg"].grid(row=1, column=2, pady=(0, row_p), sticky="nsew")
        self.labels["rem"].grid(row=2, column=0, pady=(0, 0), sticky="nsew")
        self.labels["dpm"].grid(row=2, column=1, pady=(0, 0), sticky="nsew")
        self.labels["stat"].grid(row=2, column=2, pady=(0, 0), sticky="nsew")
        self.values["rem"].grid(row=3, column=0, pady=(0, 0), sticky="nsew")
        self.values["dpm"].grid(row=3, column=1, pady=(0, 0), sticky="nsew")
        self.values["stat"].grid(row=3, column=2, pady=(0, 0), sticky="nsew")
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

    def start_move(self, event):
        self._drag_data["x"] = event.x_root - self.winfo_x()
        self._drag_data["y"] = event.y_root - self.winfo_y()

    def stop_move(self, event):
        pass

    def do_move(self, event):
        nx = event.x_root - self._drag_data["x"]
        ny = event.y_root - self._drag_data["y"]
        self.geometry(f"+{nx}+{ny}")

    # UI: Real-time metric push to HUD labels
    def update_metrics(self, combat_time, dps, dpm, total_dmg, status, rem_time):
        self.values["time"].config(text=combat_time)
        self.values["dps"].config(text=f"{dps:,.0f}")
        self.values["dmg"].config(text=f"{total_dmg:,.0f}")
        self.values["rem"].config(text=rem_time)
        self.values["dpm"].config(text=f"{dpm:,.0f}", fg=get_dpm_color(dpm))
        st = status.split(": ")[-1].upper() if ": " in status else status.upper()
        self.values["stat"].config(text=st)
        if "COMBAT" in st or "ACTIVE" in st:
            self.values["stat"].config(fg="#FF4444")
        elif "FINISHED" in st:
            self.values["stat"].config(fg="#FFD700")
        elif "WAITING" in st or "READY" in st:
            self.values["stat"].config(fg="#66CCFF")
        else:
            self.values["stat"].config(fg="#00FF00")


# Main Dashboard: Management console for window selection and analytics
class BossDPSMonitorGUI:
    def __init__(self, root):
        self.root = root

        # System: Obtain exact Windows Scale Factor (e.g., 175% = 1.75)
        # We use your current 1.75x setup as the "REFERENCE" for the satisfying look
        REFERENCE_SCALE = 1.75
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

        # UI: 'Looks the same' Logic (Proportional to scaling_factor/resolution)
        # Reference Baseline: 3840x2160 (4K) @ 1.75 scaling
        # We want the window to occupy the same PERCENTAGE of the screen
        REF_W, REF_H = 3840.0, 2160.0
        REF_SCALE = 1.75

        # Calculate how much of the screen the "satisfying" UI takes up (percentage)
        # Width: 650 / 3840 = ~16.9% | Height: 1500 / 2160 = ~69.4%
        W_RATIO = 650.0 / REF_W
        H_RATIO = 1500.0 / REF_H

        # Physical window size: strictly tied to screen resolution
        win_w = int(screen_w * W_RATIO)
        # We clamp height to 90% of screen as a safety limit
        win_h = int(min(screen_h * H_RATIO, screen_h * 0.9))

        # Calculate internal element scaling (ui_scale)
        # This is based on the logical density of the workspace
        logical_h = screen_h / current_scaling
        ref_logical_h = REF_H / REF_SCALE
        self.ui_scale = logical_h / ref_logical_h

        self.root.title("MapleStory Boss DPM Monitor v20260329.6")
        self.root.geometry(f"{win_w}x{win_h}")

        self.font_name = "Google Sans"
        try:
            test_font = tkfont.Font(family=self.font_name)
            if test_font.actual()["family"] != self.font_name:
                self.font_name = "Segoe UI"
        except:
            self.font_name = "Segoe UI"

        # Scaling Fonts: Proportional to logical height
        self.font_large = (self.font_name, int(16 * self.ui_scale), "bold")
        self.font_medium = (self.font_name, int(12 * self.ui_scale))
        self.font_small = (self.font_name, int(10 * self.ui_scale))

        # UI Styling: Modern proportional look
        style = ttk.Style()
        style.configure(".", font=(self.font_name, int(10 * self.ui_scale)))
        style.configure("TLabel", font=(self.font_name, int(10 * self.ui_scale)))
        style.configure(
            "TLabelframe.Label", font=(self.font_name, int(11 * self.ui_scale), "bold")
        )
        style.configure("TButton", font=(self.font_name, int(10 * self.ui_scale)))
        style.configure("TCombobox", font=(self.font_name, int(10 * self.ui_scale)))

        # State: Core combat variables
        self.hp_history = []
        self.metrics_history = []
        self.total_damage = 0
        self.initial_hp = None
        self.accumulated_combat_time = 0.0
        self.is_monitoring = False
        self.is_in_combat = False
        self.fight_session_start = None
        self.last_damage_time = 0
        self.last_detected_hp = None
        self.last_hp_seen_time = 0
        self.boss_name = "Unknown"
        self.capture_region = None
        self.use_gpu = torch.cuda.is_available()
        self.gpu_name = torch.cuda.get_device_name(0) if self.use_gpu else "CPU Mode"

        # Vars: Data binding for UI updates
        self.hp_val_var = tk.StringVar(value="-")
        self.rt_dps_val_var = tk.StringVar(value="-")
        self.rt_dpm_val_var = tk.StringVar(value="-")
        self.combat_time_val_var = tk.StringVar(value="00:00:00")
        self.total_dmg_val_var = tk.StringVar(value="-")
        self.avg_dpm_val_var = tk.StringVar(value="-")
        self.rem_time_val_var = tk.StringVar(value="--:--:--")
        self.status_var = tk.StringVar(value="Engine: Ready")
        self.monitor_status_var = tk.StringVar(value="Monitoring: OFF")
        self.combat_status_var = tk.StringVar(value="Combat: IDLE")
        self.perf_var = tk.StringVar(value="Actual Hz: -")

        self.setup_ui()
        self.reader = None
        threading.Thread(target=self.init_ocr, daemon=True).start()
        self.hud = HUDOverlay(self.root)
        self.setup_hotkeys()

    # UI: Building the main control panel
    def setup_ui(self):
        # Create Status Bar first so it's pinned to the bottom
        stat_container = ttk.Frame(self.root)
        stat_container.pack(side="bottom", fill="x", padx=10, pady=(0, 2))
        stat_container.columnconfigure(2, weight=1)

        st_font = (self.font_name, int(9 * self.ui_scale))
        st_bold = (self.font_name, int(9 * self.ui_scale), "bold")

        ttk.Label(stat_container, textvariable=self.status_var, font=st_font).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(stat_container, text=f"| HW: {self.gpu_name}", font=st_font).grid(
            row=0, column=1, sticky="w", padx=10
        )
        ttk.Label(stat_container, textvariable=self.perf_var, font=st_font).grid(
            row=0, column=2, sticky="e"
        )

        ttk.Label(
            stat_container,
            textvariable=self.monitor_status_var,
            font=st_bold,
            foreground="#1976d2",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=0)
        ttk.Label(
            stat_container,
            textvariable=self.combat_status_var,
            font=st_bold,
            foreground="#FF4444",
        ).grid(row=1, column=2, sticky="e", pady=0)

        # Create a Canvas with a Scrollbar for the main content
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

        # Bind mousewheel to scrolling
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        content = self.scrollable_frame
        pad_val = int(30 * self.ui_scale)
        inner_pad = int(12 * self.ui_scale)
        pad = {"padx": pad_val, "pady": inner_pad}

        settings_f = ttk.LabelFrame(content, text=" Configuration ")
        settings_f.pack(fill="x", **pad)

        self.window_list = ttk.Combobox(settings_f, width=int(50 * self.ui_scale))
        self.window_list.pack(padx=10, pady=5)
        self.window_list.bind("<<ComboboxSelected>>", self.on_window_change)

        btn_f = ttk.Frame(settings_f)
        btn_f.pack(fill="x", padx=10, pady=5)
        ttk.Button(
            btn_f, text="Refresh Window List", command=self.refresh_windows
        ).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(
            btn_f, text="Set Capture Region (Crop)", command=self.set_region
        ).pack(side="left", fill="x", expand=True, padx=5)

        self.region_display = tk.Label(
            settings_f,
            text="REGION NOT SET",
            font=(self.font_name, int(9 * self.ui_scale), "bold"),
            fg="#C62828",
            bg="#FFEBEE",
            padx=12,
            pady=4,
            relief="flat",
            borderwidth=0,
        )
        self.region_display.pack(pady=8)

        freq_f = ttk.Frame(settings_f)
        freq_f.pack(fill="x", pady=5)
        ttk.Label(freq_f, text="Freq (Hz):").pack(side="left", padx=10)
        self.freq_var = tk.DoubleVar(value=1.0)
        ttk.Scale(
            freq_f, from_=1.0, to=10.0, variable=self.freq_var, orient="horizontal"
        ).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Label(freq_f, textvariable=self.freq_var, width=4).pack(side="left")
        ttk.Label(
            settings_f,
            text="F7: Toggle Monitoring  |  F8: Reset  |  F9: Show/Hide HUD",
            font=(self.font_name, int(10 * self.ui_scale)),
            foreground="gray",
        ).pack(pady=2)

        dash_f = ttk.LabelFrame(content, text=" Combat Data Dashboard ")
        dash_f.pack(fill="x", **pad)

        metrics_f = ttk.Frame(dash_f)
        metrics_f.pack(
            fill="x", padx=int(40 * self.ui_scale), pady=int(15 * self.ui_scale)
        )
        metrics_f.columnconfigure(1, weight=1)

        m_config = [
            ("Remaining HP", self.hp_val_var, "red"),
            ("Real-time DPS", self.rt_dps_val_var, None),
            ("Real-time DPM", self.rt_dpm_val_var, None),
            ("SEP", None, None),
            ("Combat Time", self.combat_time_val_var, None),
            ("Remaining Time", self.rem_time_val_var, "#673ab7"),
            ("Total Damage", self.total_dmg_val_var, "#388e3c"),
            ("Average DPM", self.avg_dpm_val_var, "#1976d2"),
        ]

        row_idx = 0
        for name, var, color in m_config:
            if name == "SEP":
                ttk.Separator(metrics_f, orient="horizontal").grid(
                    row=row_idx,
                    column=0,
                    columnspan=2,
                    sticky="ew",
                    pady=int(15 * self.ui_scale),
                )
                row_idx += 1
                continue
            lbl = ttk.Label(metrics_f, text=f"{name}:", font=self.font_large)
            val = ttk.Label(metrics_f, textvariable=var, font=self.font_large)
            if color:
                val.config(foreground=color)
                if name == "Remaining HP":
                    lbl.config(foreground=color)
            lbl.grid(row=row_idx, column=0, sticky="w", pady=int(8 * self.ui_scale))
            val.grid(row=row_idx, column=1, sticky="e", pady=int(8 * self.ui_scale))
            row_idx += 1

        ttk.Button(
            content, text="GENERATE PNG REPORT", command=self.generate_report
        ).pack(padx=pad_val, pady=5, fill="x")

        self.refresh_windows()

    def _on_canvas_configure(self, event):
        # Update the width of the scrollable frame to match the canvas
        self.main_canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # UI: Reset region when window selection changes
    def on_window_change(self, event=None):
        self.capture_region = None
        self.region_display.config(text="REGION NOT SET", fg="#C62828", bg="#FFEBEE")

    # System: Initialize EasyOCR engine with GPU/CPU support
    def init_ocr(self):
        try:
            self.reader = easyocr.Reader(["en", "ch_tra"], gpu=self.use_gpu)
            self.status_var.set("Engine: Ready")
        except Exception as e:
            self.status_var.set(f"OCR Error: {str(e)[:20]}")
            with open("debug_ocr_error.txt", "a") as f:
                f.write(f"[{datetime.now()}] Init Error: {str(e)}\n")

    # System: Global hotkey registration
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

    # UI: Interactive crop tool for defining HP bar location
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
                # Update status label to success pill state
                self.region_display.config(
                    text="REGION CUSTOM SET", fg="#2E7D32", bg="#E8F5E9"
                )

    # State: Toggle the background monitoring thread
    def toggle_monitoring(self):
        if self.is_monitoring:
            self.is_monitoring = False
            if self.is_in_combat and self.fight_session_start:
                self.accumulated_combat_time += time.time() - self.fight_session_start
            self.is_in_combat = False
            self.monitor_status_var.set("Monitoring: OFF")
            self.combat_status_var.set("Combat: IDLE")
            self.hud.update_metrics(
                self.format_combat_time(self.accumulated_combat_time, short=True),
                0,
                0,
                self.total_damage,
                "IDLE",
                "--:--",
            )
        else:
            if not self.reader:
                return
            selection = self.window_list.get()
            windows = gw.getWindowsWithTitle(selection)
            if not windows:
                return
            self.target_window = windows[0]
            self.is_monitoring = True
            self.monitor_status_var.set("Monitoring: ON")
            self.combat_status_var.set("Combat: WAITING")
            self.hud.update_metrics("00:00", 0, 0, self.total_damage, "READY", "--:--")
            threading.Thread(target=self.monitor_loop, daemon=True).start()

    # State: Clear all combat data
    def reset_metrics(self):
        self.hp_history = []
        self.metrics_history = []
        self.total_damage = 0
        self.initial_hp = None
        self.accumulated_combat_time = 0.0
        self.fight_session_start = None
        self.is_in_combat = False
        self.last_detected_hp = None
        self.last_hp_seen_time = 0
        self.boss_name = "Unknown"
        self.hp_val_var.set("-")
        self.rt_dps_val_var.set("-")
        self.rt_dpm_val_var.set("-")
        self.combat_time_val_var.set("00:00:00")
        self.total_dmg_val_var.set("-")
        self.avg_dpm_val_var.set("-")
        self.rem_time_val_var.set("--:--:--")
        self.combat_status_var.set(
            "Combat: WAITING" if self.is_monitoring else "Combat: IDLE"
        )
        self.hud.update_metrics(
            "00:00", 0, 0, 0, "READY" if self.is_monitoring else "IDLE", "00:00"
        )

    # Engine: Parse raw text results into numeric HP values
    def parse_hp(self, text):
        matches = re.findall(r"(\d{1,3}(?:,\d{3})*)", text)
        valid = [
            int(m.replace(",", ""))
            for m in matches
            if 100 < int(m.replace(",", "")) < 10**15
        ]
        return max(valid) if valid else None

    # UI: Helper to format seconds into HH:MM:SS
    def format_combat_time(self, seconds, short=False):
        td = timedelta(seconds=int(max(0, seconds)))
        parts = str(td).split(":")
        return (
            f"{int(parts[1]):02d}:{int(parts[2]):02d}"
            if short
            else f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
        )

    # Engine: Main monitoring loop running in a separate thread
    def monitor_loop(self):
        with mss.mss() as sct:
            while self.is_monitoring:
                loop_start = time.time()
                target_hz = self.freq_var.get()
                interval = 1.0 / target_hz
                win = self.target_window
                if win.isMinimized or not win.visible:
                    time.sleep(interval)
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
                img = np.array(sct.grab(monitor))
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                results = []
                try:
                    results = self.reader.readtext(img, detail=0)
                except Exception as e:
                    with open("debug_ocr_error.txt", "a") as f:
                        f.write(f"[{datetime.now()}] Runtime Error: {str(e)}\n")

                current_hp = None
                now = time.time()
                if results:
                    full_text = " ".join(results)
                    hp = self.parse_hp(full_text)
                    if hp and not self.is_outlier(hp, now):
                        current_hp = hp

                    # Engine: Extract Boss Name (non-numeric text)
                    # We look for strings that don't contain many digits and aren't just punctuation/symbols
                    name_candidates = [
                        re.sub(r"[0-9,.\-%/()\[\]]", "", res).strip() for res in results
                    ]
                    # Filter out empty or very short noise strings
                    valid_names = [n for n in name_candidates if len(n) > 1]
                    if valid_names:
                        # Keep the longest detected string as the potential boss name
                        detected_name = max(valid_names, key=len)
                        if detected_name:
                            self.boss_name = detected_name

                if current_hp:
                    self.last_hp_seen_time = now
                    if self.last_detected_hp is None:
                        self.last_detected_hp = current_hp
                    if not self.is_in_combat and current_hp < self.last_detected_hp:
                        self.is_in_combat = True
                        self.fight_session_start = now
                        self.last_damage_time = now
                        if self.initial_hp is None:
                            self.initial_hp = self.last_detected_hp
                        self.combat_status_var.set("Combat: ACTIVE")
                    if self.is_in_combat:
                        if current_hp < self.last_detected_hp:
                            self.last_damage_time = now
                        if now - self.last_damage_time >= 3.0:
                            self.is_in_combat = False
                            self.accumulated_combat_time += (
                                time.time() - self.fight_session_start
                            )
                            self.fight_session_start = None
                            self.combat_status_var.set("Combat: PAUSED")
                    self.last_detected_hp = current_hp
                    self.hp_history.append((now, current_hp))
                    if self.initial_hp is not None:
                        self.total_damage = max(0, self.initial_hp - current_hp)
                    total_time = self.accumulated_combat_time + (
                        now - self.fight_session_start
                        if (self.is_in_combat and self.fight_session_start)
                        else 0.0
                    )
                    self.hp_val_var.set(f"{current_hp:,}")
                    if total_time > 0:
                        past_idx = max(0, len(self.hp_history) - int(5 * target_hz) - 1)
                        dt_recent = now - self.hp_history[past_idx][0]
                        rt_dps = (
                            max(
                                0,
                                (self.hp_history[past_idx][1] - current_hp) / dt_recent,
                            )
                            if dt_recent > 0
                            else 0
                        )
                        avg_dpm = (self.total_damage / total_time) * 60
                        c_time_str = self.format_combat_time(total_time)
                        rem_sec = (current_hp / (avg_dpm / 60)) if avg_dpm > 0 else 0
                        rem_t_str = self.format_combat_time(rem_sec, short=True)
                        self.rt_dps_val_var.set(f"{rt_dps:,.0f}")
                        self.rt_dpm_val_var.set(f"{rt_dps * 60:,.0f}")
                        self.combat_time_val_var.set(f"{c_time_str}")
                        self.total_dmg_val_var.set(f"{self.total_damage:,}")
                        self.avg_dpm_val_var.set(f"{avg_dpm:,.0f}")
                        self.rem_time_val_var.set(f"{rem_t_str}")
                        self.hud.update_metrics(
                            self.format_combat_time(total_time, short=True),
                            rt_dps,
                            avg_dpm,
                            self.total_damage,
                            "IN COMBAT" if self.is_in_combat else "READY",
                            rem_t_str,
                        )
                    else:
                        self.hud.update_metrics(
                            "00:00", 0, 0, self.total_damage, "READY", "--:--"
                        )
                else:
                    if self.is_in_combat and now - self.last_hp_seen_time >= 3.0:
                        self.is_in_combat = False
                        f_ts = self.last_hp_seen_time + interval
                        self.accumulated_combat_time += f_ts - self.fight_session_start
                        self.fight_session_start = None
                        if self.initial_hp is not None:
                            self.total_damage = self.initial_hp
                        self.hp_val_var.set("0")
                        final_avg_dpm = (
                            self.total_damage / self.accumulated_combat_time
                        ) * 60
                        self.combat_status_var.set("Combat: FINISHED")
                        self.hud.update_metrics(
                            self.format_combat_time(
                                self.accumulated_combat_time, short=True
                            ),
                            0,
                            final_avg_dpm,
                            self.total_damage,
                            "FINISHED",
                            "00:00",
                        )
                elapsed = time.time() - loop_start
                self.perf_var.set(f"Actual Hz: {1.0/max(0.001, elapsed):.1f}")
                time.sleep(max(0, interval - elapsed))

    # Engine: Reject visual noise or OCR errors
    def is_outlier(self, hp, now):
        if self.last_detected_hp is None:
            return False
        # Rule 1: Reject HP increase over 50,000 or decrease over 500,000
        if hp > self.last_detected_hp + 50000 or hp < self.last_detected_hp - 500000:
            return True
        return False

    # Analytics: Generate and save PNG performance graph
    def generate_report(self):
        if not self.hp_history:
            messagebox.showwarning("Warning", "No combat data to report.")
            return
        try:
            # Data: Processing raw history into DPS samples
            df_raw = pd.DataFrame(self.hp_history, columns=["Timestamp", "HP"])
            df_raw["TimeSec"] = df_raw["Timestamp"] - df_raw["Timestamp"].iloc[0]
            df_raw["HP_Diff"] = df_raw["HP"].shift(1) - df_raw["HP"]
            df_raw["Time_Diff"] = df_raw["Timestamp"].diff()
            df_raw["RT_DPS"] = (df_raw["HP_Diff"] / df_raw["Time_Diff"]).fillna(0)
            df_raw = df_raw[df_raw["RT_DPS"] >= 0]

            if len(df_raw) < 5:
                messagebox.showwarning("Warning", "Not enough data for smoothing.")
                return

            # Signal Processing: Advanced Smoothing (Savitzky-Golay + Spline)
            # 1. Apply Savitzky-Golay to remove noise while preserving burst peaks
            # Note: We increase the window_len and use a lower polyorder for a smoother curve
            window_len = min(len(df_raw) // 2, 51)
            if window_len % 2 == 0:
                window_len += 1
            if window_len < 5:
                window_len = 5
            smoothed_dps = savgol_filter(df_raw["RT_DPS"], window_len, 2)

            # 2. Resample using Cubic Spline for a continuous, mathematically smooth curve
            time_new = np.linspace(
                df_raw["TimeSec"].min(), df_raw["TimeSec"].max(), 500
            )
            spline = make_interp_spline(df_raw["TimeSec"], smoothed_dps, k=3)
            interp_dps = spline(time_new)
            interp_dps = np.clip(interp_dps, 0, None)  # Ensure no negative DPS

            # Visualization: Styled Seaborn curve plot
            sns.set_theme(style="whitegrid", font=self.font_name)
            plt.figure(figsize=(12, 7))

            # Use lineplot with area fill for an attractive "illustration" look
            sns.lineplot(x=time_new, y=interp_dps, color="#1976d2", linewidth=2.5)
            plt.fill_between(time_new, interp_dps, color="#1976d2", alpha=0.15)

            # Metrics: Calculate summary stats
            total_t = self.accumulated_combat_time + (
                time.time() - self.fight_session_start
                if (self.is_in_combat and self.fight_session_start)
                else 0.0
            )
            avg_dps = self.total_damage / max(0.1, total_t)

            # Reference: Average DPS line
            plt.axhline(
                y=avg_dps,
                color="#D32F2F",
                linestyle="--",
                alpha=0.8,
                label="Average DPS",
            )

            # Styling: Professional axes and titles
            plt.title("BOSS DPS/DPM Analysis", fontsize=18, pad=20, weight="bold")
            plt.xlabel("Combat Duration (Seconds)", fontsize=12)
            plt.ylabel("Damage Per Second (DPS)", fontsize=12)
            plt.ylim(0, max(interp_dps.max(), avg_dps) * 1.3)
            plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
            plt.legend(frameon=True, facecolor="white")

            # Summary: Pill-style text box for overview
            # Note: We use fixed-width padding to align labels left (<15) and values right (>15)
            summary_text = (
                f"{'Combat Time':<15} : {self.format_combat_time(total_t):>15}\n"
                f"{'Total Damage':<15} : {self.total_damage:>15,}\n"
                f"{'Average DPS':<15} : {avg_dps:>15,.0f}\n"
                f"{'Average DPM':<15} : {avg_dps*60:>15,.0f}"
            )
            plt.text(
                0.02,
                0.96,
                summary_text,
                transform=plt.gca().transAxes,
                verticalalignment="top",
                family="monospace",
                fontsize=11,
                bbox=dict(
                    boxstyle="round,pad=1",
                    facecolor="white",
                    edgecolor="#DDDDDD",
                    alpha=0.95,
                ),
            )

            plt.tight_layout()
            fname = f"Boss_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(fname, dpi=150)
            plt.close()
            messagebox.showinfo("Success", f"Report saved: {fname}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = BossDPSMonitorGUI(root)
    root.mainloop()
