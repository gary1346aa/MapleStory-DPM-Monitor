import cv2
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
from PIL import Image, ImageTk
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import datetime, timedelta
import os
import ctypes
import keyboard

# 1. Enable High DPI awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 2. Monkeypatch torch.load
_original_torch_load = torch.load


def _patched_torch_load(*args, **kwargs):
    if "weights_only" in kwargs:
        del kwargs["weights_only"]
    return _original_torch_load(*args, **kwargs)


torch.load = _patched_torch_load


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

        # Sliders
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

        self.container = tk.Frame(self, bg="black")
        self.container.pack(padx=5, pady=(12, 5))

        self.setup_widgets()
        self.update_layout()
        self._drag_data = {"x": 0, "y": 0}
        self.bind_drag(self.container)
        self.bind("<Enter>", self.show_controls)
        self.bind("<Leave>", self.hide_controls)
        self.withdraw()

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

    def bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self.start_move)
        widget.bind("<ButtonRelease-1>", self.stop_move)
        widget.bind("<B1-Motion>", self.do_move)
        for child in widget.winfo_children():
            self.bind_drag(child)

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


class BossDPSMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MapleStory Boss DPS Monitor")
        self.root.geometry("650x1500") # Extreme height as requested
        self.font_name = "Google Sans"
        try:
            test_font = tkfont.Font(family=self.font_name)
            if test_font.actual()["family"] != self.font_name:
                self.font_name = "Segoe UI"
        except:
            self.font_name = "Segoe UI"
        
        self.font_large = (self.font_name, 16, "bold")
        self.font_medium = (self.font_name, 12)
        self.font_small = (self.font_name, 10)
        
        # Configure global style
        style = ttk.Style()
        style.configure(".", font=(self.font_name, 10))
        style.configure("TLabel", font=(self.font_name, 10))
        style.configure("TLabelframe.Label", font=(self.font_name, 11, "bold"))
        style.configure("TButton", font=(self.font_name, 10))
        style.configure("TCombobox", font=(self.font_name, 10))

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
        self.capture_region = None
        self.use_gpu = torch.cuda.is_available()
        self.gpu_name = torch.cuda.get_device_name(0) if self.use_gpu else "CPU Mode"
        
        # Initialize variables before setup_ui
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

    def setup_ui(self):
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True)
        
        content = ttk.Frame(main_container)
        content.pack(fill="both", expand=True)
        
        pad = {"padx": 30, "pady": 12}
        settings_f = ttk.LabelFrame(content, text=" Configuration ")
        settings_f.pack(fill="x", **pad)
        
        self.window_list = ttk.Combobox(settings_f, width=50)
        self.window_list.pack(padx=10, pady=5)
        
        btn_f = ttk.Frame(settings_f)
        btn_f.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_f, text="Refresh Window List", command=self.refresh_windows).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(btn_f, text="Set Capture Region (Crop)", command=self.set_region).pack(side="left", fill="x", expand=True, padx=5)
        
        self.region_var = tk.StringVar(value="Region: Default")
        ttk.Label(settings_f, textvariable=self.region_var).pack()
        
        freq_f = ttk.Frame(settings_f)
        freq_f.pack(fill="x", pady=5)
        ttk.Label(freq_f, text="Freq (Hz):").pack(side="left", padx=10)
        self.freq_var = tk.DoubleVar(value=5.0)
        ttk.Scale(freq_f, from_=1.0, to=10.0, variable=self.freq_var, orient="horizontal").pack(side="left", fill="x", expand=True, padx=10)
        ttk.Label(freq_f, textvariable=self.freq_var, width=4).pack(side="left")
        ttk.Label(settings_f, text="F7: Toggle Monitoring  |  F8: Reset  |  F9: Show/Hide HUD", font=(self.font_name, 10), foreground="gray").pack(pady=2)

        dash_f = ttk.LabelFrame(content, text=" Combat Data Dashboard ")
        dash_f.pack(fill="x", **pad)

        metrics_f = ttk.Frame(dash_f)
        metrics_f.pack(fill="x", padx=40, pady=15)
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
                ttk.Separator(metrics_f, orient="horizontal").grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=15)
                row_idx += 1
                continue
            lbl = ttk.Label(metrics_f, text=f"{name}:", font=self.font_large)
            val = ttk.Label(metrics_f, textvariable=var, font=self.font_large)
            if color:
                val.config(foreground=color)
                if name == "Remaining HP": lbl.config(foreground=color)
            lbl.grid(row=row_idx, column=0, sticky="w", pady=8)
            val.grid(row=row_idx, column=1, sticky="e", pady=8)
            row_idx += 1

        ttk.Button(content, text="GENERATE PNG REPORT", command=self.generate_report).pack(padx=30, pady=5, fill="x")

        # TWO-LINE SYSTEM STATUS BAR (Tightened with grid)
        stat_container = ttk.Frame(self.root)
        stat_container.pack(side="bottom", fill="x", padx=10, pady=(0, 2))
        stat_container.columnconfigure(2, weight=1)

        st_font = (self.font_name, 9)
        st_bold = (self.font_name, 9, "bold")
        
        # Row 0: Engine, HW, Actual Hz
        ttk.Label(stat_container, textvariable=self.status_var, font=st_font).grid(row=0, column=0, sticky="w")
        ttk.Label(stat_container, text=f"| HW: {self.gpu_name}", font=st_font).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(stat_container, textvariable=self.perf_var, font=st_font).grid(row=0, column=2, sticky="e")
        
        # Row 1: Monitoring and Combat (No vertical pady to keep them tight)
        ttk.Label(stat_container, textvariable=self.monitor_status_var, font=st_bold, foreground="#1976d2").grid(row=1, column=0, columnspan=2, sticky="w", pady=0)
        ttk.Label(stat_container, textvariable=self.combat_status_var, font=st_bold, foreground="#FF4444").grid(row=1, column=2, sticky="e", pady=0)

        self.refresh_windows()

    def init_ocr(self):
        try:
            self.reader = easyocr.Reader(["en"], gpu=self.use_gpu)
            self.status_var.set("Engine: Ready")
        except Exception:
            pass

    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey("f7", self.hotkey_toggle)
            keyboard.add_hotkey("f8", self.hotkey_reset)
            keyboard.add_hotkey("f9", self.hotkey_hud)
        except Exception:
            pass

    def hotkey_toggle(self): self.root.after(0, self.toggle_monitoring)
    def hotkey_reset(self): self.root.after(0, self.reset_metrics)
    def hotkey_hud(self): self.root.after(0, self.toggle_hud)

    def toggle_hud(self):
        if self.hud.winfo_viewable(): self.hud.withdraw()
        else: self.hud.deiconify()

    def refresh_windows(self):
        titles = [w for w in gw.getAllTitles() if w.strip()]
        self.window_list["values"] = titles
        if titles: self.window_list.current(0)

    def set_region(self):
        selection = self.window_list.get()
        windows = gw.getWindowsWithTitle(selection)
        if not windows: return
        win = windows[0]
        with mss.mss() as sct:
            monitor = {"top": win.top, "left": win.left, "width": win.width, "height": win.height}
            sct_img = sct.grab(monitor)
            screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            selector = RegionSelector(self.root, screenshot)
            self.root.wait_window(selector)
            if selector.selection:
                self.capture_region = selector.selection
                self.region_var.set(f"Region Set")

    def toggle_monitoring(self):
        if self.is_monitoring:
            self.is_monitoring = False
            if self.is_in_combat and self.fight_session_start:
                self.accumulated_combat_time += time.time() - self.fight_session_start
            self.is_in_combat = False
            self.monitor_status_var.set("Monitoring: OFF")
            self.combat_status_var.set("Combat: IDLE")
            self.hud.update_metrics(self.format_combat_time(self.accumulated_combat_time, short=True), 0, 0, self.total_damage, "IDLE", "--:--")
        else:
            if not self.reader: return
            selection = self.window_list.get()
            windows = gw.getWindowsWithTitle(selection)
            if not windows: return
            self.target_window = windows[0]
            self.is_monitoring = True
            self.monitor_status_var.set("Monitoring: ON")
            self.combat_status_var.set("Combat: WAITING")
            self.hud.update_metrics("00:00", 0, 0, self.total_damage, "READY", "--:--")
            threading.Thread(target=self.monitor_loop, daemon=True).start()

    def reset_metrics(self):
        self.hp_history = []; self.metrics_history = []; self.total_damage = 0; self.initial_hp = None; self.accumulated_combat_time = 0.0
        self.fight_session_start = None; self.is_in_combat = False; self.last_detected_hp = None; self.last_hp_seen_time = 0
        self.hp_val_var.set("-"); self.rt_dps_val_var.set("-"); self.rt_dpm_val_var.set("-"); self.combat_time_val_var.set("00:00:00")
        self.total_dmg_val_var.set("-"); self.avg_dpm_val_var.set("-"); self.rem_time_val_var.set("--:--:--")
        self.combat_status_var.set("Combat: WAITING" if self.is_monitoring else "Combat: IDLE")
        self.hud.update_metrics("00:00", 0, 0, 0, "READY" if self.is_monitoring else "IDLE", "00:00")

    def parse_hp(self, text):
        matches = re.findall(r"(\d{1,3}(?:,\d{3})*)", text)
        valid = [int(m.replace(",", "")) for m in matches if 100 < int(m.replace(",", "")) < 10**15]
        return max(valid) if valid else None

    def format_combat_time(self, seconds, short=False):
        td = timedelta(seconds=int(max(0, seconds)))
        parts = str(td).split(":")
        return (f"{int(parts[1]):02d}:{int(parts[2]):02d}" if short else f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}")

    def monitor_loop(self):
        with mss.mss() as sct:
            while self.is_monitoring:
                loop_start = time.time(); target_hz = self.freq_var.get(); interval = 1.0 / target_hz; win = self.target_window
                if win.isMinimized or not win.visible: time.sleep(interval); continue
                monitor = ({"top": win.top + self.capture_region[1], "left": win.left + self.capture_region[0], "width": self.capture_region[2], "height": self.capture_region[3]} if self.capture_region else {"top": win.top, "left": win.left, "width": win.width, "height": int(win.height * 0.35)})
                img = np.array(sct.grab(monitor)); img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                results = self.reader.readtext(img, detail=0); current_hp = None
                if results:
                    full_text = " ".join(results); hp = self.parse_hp(full_text)
                    if hp and not self.is_outlier(hp): current_hp = hp
                now = time.time()
                if current_hp:
                    self.last_hp_seen_time = now
                    if self.last_detected_hp is None: self.last_detected_hp = current_hp
                    if not self.is_in_combat and current_hp < self.last_detected_hp:
                        self.is_in_combat = True; self.fight_session_start = now; self.last_damage_time = now
                        if self.initial_hp is None: self.initial_hp = self.last_detected_hp
                        self.combat_status_var.set("Combat: ACTIVE")
                    if self.is_in_combat:
                        if current_hp < self.last_detected_hp: self.last_damage_time = now
                        if now - self.last_damage_time >= 3.0:
                            self.is_in_combat = False; self.accumulated_combat_time += time.time() - self.fight_session_start
                            self.fight_session_start = None; self.combat_status_var.set("Combat: PAUSED")
                    self.last_detected_hp = current_hp; self.hp_history.append((now, current_hp))
                    if self.initial_hp is not None: self.total_damage = max(0, self.initial_hp - current_hp)
                    total_time = self.accumulated_combat_time + (now - self.fight_session_start if (self.is_in_combat and self.fight_session_start) else 0.0)
                    self.hp_val_var.set(f"{current_hp:,}")
                    if total_time > 0:
                        past_idx = max(0, len(self.hp_history) - int(5 * target_hz) - 1); dt_recent = now - self.hp_history[past_idx][0]
                        rt_dps = max(0, (self.hp_history[past_idx][1] - current_hp) / dt_recent) if dt_recent > 0 else 0
                        avg_dpm = (self.total_damage / total_time) * 60; c_time_str = self.format_combat_time(total_time); rem_sec = (current_hp / (avg_dpm / 60)) if avg_dpm > 0 else 0; rem_t_str = self.format_combat_time(rem_sec, short=True)
                        self.rt_dps_val_var.set(f"{rt_dps:,.0f}"); self.rt_dpm_val_var.set(f"{rt_dps * 60:,.0f}"); self.combat_time_val_var.set(f"{c_time_str}"); self.total_dmg_val_var.set(f"{self.total_damage:,}"); self.avg_dpm_val_var.set(f"{avg_dpm:,.0f}"); self.rem_time_val_var.set(f"{rem_t_str}")
                        self.hud.update_metrics(self.format_combat_time(total_time, short=True), rt_dps, avg_dpm, self.total_damage, "IN COMBAT" if self.is_in_combat else "READY", rem_t_str)
                    else: self.hud.update_metrics("00:00", 0, 0, self.total_damage, "READY", "--:--")
                else:
                    if self.is_in_combat and now - self.last_hp_seen_time >= 3.0:
                        self.is_in_combat = False; f_ts = self.last_hp_seen_time + interval
                        self.accumulated_combat_time += f_ts - self.fight_session_start; self.fight_session_start = None
                        if self.initial_hp is not None: self.total_damage = self.initial_hp
                        self.hp_val_var.set("0"); final_avg_dpm = (self.total_damage / self.accumulated_combat_time) * 60; self.combat_status_var.set("Combat: FINISHED"); self.hud.update_metrics(self.format_combat_time(self.accumulated_combat_time, short=True), 0, final_avg_dpm, self.total_damage, "FINISHED", "00:00")
                elapsed = time.time() - loop_start; self.perf_var.set(f"Actual Hz: {1.0/max(0.001, elapsed):.1f}"); time.sleep(max(0, interval - elapsed))

    def is_outlier(self, hp):
        if self.last_detected_hp is None: return False
        if self.last_detected_hp < 500000: return hp > self.last_detected_hp * 1.05
        if hp < self.last_detected_hp * 0.01: return True
        if self.last_detected_hp * 1.02 < hp < self.last_detected_hp * 2: return True
        return False

    def generate_report(self):
        if not self.hp_history:
            messagebox.showwarning("Warning", "No combat data to report."); return
        try:
            df = pd.DataFrame(self.hp_history, columns=["Timestamp", "HP"])
            df["Time_Diff"] = df["Timestamp"].diff(); df["HP_Diff"] = df["HP"].shift(1) - df["HP"]; df["RT_DPS"] = df["HP_Diff"] / df["Time_Diff"]
            df = df[df["RT_DPS"] > 0].copy()
            if df.empty: messagebox.showwarning("Warning", "Not enough damage data for report."); return
            df["TimeSec"] = df["Timestamp"] - df["Timestamp"].iloc[0]; df["RT_DPS_Smooth"] = df["RT_DPS"].rolling(window=3, center=True).median().fillna(df["RT_DPS"])
            plt.figure(figsize=(12, 8)); plt.plot(df["TimeSec"], df["RT_DPS_Smooth"], label="Real-time DPS", color="#1976d2", linewidth=2)
            total_t = self.accumulated_combat_time + (time.time() - self.fight_session_start if (self.is_in_combat and self.fight_session_start) else 0.0)
            avg_dps = self.total_damage / max(0.1, total_t); plt.axhline(y=avg_dps, color="red", linestyle="--", label="Average DPS"); plt.ylim(0, max(df["RT_DPS_Smooth"].max(), avg_dps) * 1.4); plt.gca().yaxis.set_major_locator(ticker.MultipleLocator(10000)); plt.title("Performance Analytics", fontname=self.font_name, fontsize=16, pad=20); plt.xlabel("Seconds", fontname=self.font_name); plt.ylabel("DPS", fontname=self.font_name); plt.legend(); plt.grid(True, alpha=0.3)
            summary = (f"{'Combat Time':<19} : {self.format_combat_time(total_t):>15}\n" f"{'Total Damage':<19} : {self.total_damage:>15,}\n" f"{'Average DPS':<19} : {avg_dps:>15,.0f}\n" f"{'Average DPM':<19} : {avg_dps*60:>15,.0f}")
            plt.text(0.02, 0.98, summary, transform=plt.gca().transAxes, verticalalignment="top", bbox=dict(boxstyle="round,pad=0.8", facecolor="white", edgecolor="gray", alpha=0.9), fontsize=12, family=self.font_name)
            plt.tight_layout(); fname = f"Pro_Boss_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"; plt.savefig(fname, dpi=150); plt.close(); messagebox.showinfo("Success", f"Report saved: {fname}")
        except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk(); app = BossDPSMonitorGUI(root); root.mainloop()
