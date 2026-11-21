#!/usr/bin/env python3
"""
RasPi Hunter Floating Menu
Butang menu terapung (always-on-top) sahaja untuk paparan skrin penuh sedia ada.
Menyediakan penukar Wi-Fi (NetworkManager/nmcli) serta kawalan kuasa (Restart/Shutdown).
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path

DEFAULT_CONFIG = {
    "title": "KAWALAN SISTEM & WI-FI",
    "button_text": "⚙ MENU",
    "screen_width": "auto",
    "screen_height": "auto",
    "button_x": "auto",
    "button_y": 3,
    "button_width": 78,
    "button_height": 30,
    "wifi_interface": "wlan0",
    "keep_on_top_ms": 800,
    "wifi_profiles": [],
}


def find_config_path(cli_path: str | None = None) -> Path | None:
    """Cari fail konfigurasi mengikut keutamaan."""
    candidates: list[Path] = []
    if cli_path:
        candidates.append(Path(cli_path).expanduser())
    env_path = os.environ.get("FLOATING_MENU_CONFIG")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    script_dir = Path(__file__).resolve().parent
    candidates.append(script_dir / "config.json")
    candidates.append(Path.home() / ".config" / "raspi-hunter-floating-menu" / "config.json")

    for path in candidates:
        if path.is_file():
            return path
    return None


def load_config(cli_path: str | None = None) -> dict:
    """Muat konfigurasi daripada fail JSON dan gabungkan dengan nilai lalai."""
    cfg = dict(DEFAULT_CONFIG)
    config_path = find_config_path(cli_path)
    if config_path is None:
        return cfg

    try:
        with config_path.open("r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        if isinstance(user_cfg, dict):
            cfg.update(user_cfg)
    except Exception as exc:
        print(f"[AMARAN] Gagal membaca konfigurasi {config_path}: {exc}", file=sys.stderr)

    normalized_profiles = []
    for item in cfg.get("wifi_profiles", []):
        if not isinstance(item, dict):
            continue
        ssid = str(item.get("ssid", "")).strip()
        con_name = str(item.get("con_name", "") or ssid).strip()
        label = str(item.get("label", "") or ssid or con_name).strip()
        if not ssid and not con_name:
            continue
        normalized_profiles.append(
            {
                "label": label,
                "con_name": con_name,
                "ssid": ssid or con_name,
            }
        )
    cfg["wifi_profiles"] = normalized_profiles
    return cfg


def run_privileged(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    """Jalankan arahan terus dahulu; jika gagal kebenaran, cuba semula dengan sudo -n."""
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if res.returncode == 0:
        return res

    stderr_lower = (res.stderr or "").lower()
    needs_priv = any(
        kw in stderr_lower
        for kw in ("not authorized", "permission denied", "insufficient privileges", "interactive authentication")
    )
    if needs_priv and os.geteuid() != 0:
        return subprocess.run(
            ["sudo", "-n", *cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    return res


def get_current_wifi_and_ip(wifi_interface: str = "wlan0") -> tuple[str, str]:
    ssid = "Tiada sambungan"
    ip_addr = "-"
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
            text=True,
            timeout=3,
        )
        for line in out.splitlines():
            if line.startswith("yes:"):
                ssid = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass

    try:
        out_ip = subprocess.check_output(
            ["nmcli", "-g", "IP4.ADDRESS", "dev", "show", wifi_interface],
            text=True,
            timeout=3,
        ).strip()
        if out_ip:
            ip_addr = out_ip.splitlines()[0].split("/")[0]
    except Exception:
        pass

    return ssid, ip_addr


def resolve_int(value, fallback: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        if parsed > 0:
            return parsed
    return fallback


class RasPiHunterFloatingMenu:
    def __init__(self, root: tk.Tk, config: dict):
        self.root = root
        self.config = config
        self.wifi_profiles: list[dict] = config.get("wifi_profiles", [])
        self.wifi_interface: str = str(config.get("wifi_interface", "wlan0"))
        self.keep_on_top_ms: int = max(250, resolve_int(config.get("keep_on_top_ms"), 800))

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0f172a")

        detected_w = self.root.winfo_screenwidth() or 480
        detected_h = self.root.winfo_screenheight() or 320
        self.screen_w = resolve_int(config.get("screen_width"), detected_w)
        self.screen_h = resolve_int(config.get("screen_height"), detected_h)

        self.btn_w = resolve_int(config.get("button_width"), 78)
        self.btn_h = resolve_int(config.get("button_height"), 30)

        default_x = max(0, self.screen_w - self.btn_w - 12)
        raw_x = config.get("button_x", "auto")
        raw_y = config.get("button_y", 3)

        if isinstance(raw_x, int):
            self.pos_x = max(0, min(self.screen_w - self.btn_w, raw_x))
        elif isinstance(raw_x, str) and raw_x.isdigit():
            self.pos_x = max(0, min(self.screen_w - self.btn_w, int(raw_x)))
        else:
            self.pos_x = default_x

        if isinstance(raw_y, int):
            self.pos_y = max(0, min(self.screen_h - self.btn_h, raw_y))
        elif isinstance(raw_y, str) and raw_y.isdigit():
            self.pos_y = max(0, min(self.screen_h - self.btn_h, int(raw_y)))
        else:
            self.pos_y = 3

        self.root.geometry(f"{self.btn_w}x{self.btn_h}+{self.pos_x}+{self.pos_y}")

        self._drag_start_x = 0
        self._drag_start_y = 0
        self._moved = False

        self.fab = tk.Label(
            self.root,
            text=str(config.get("button_text", "⚙ MENU")),
            font=("Sans", 9, "bold"),
            fg="#ffffff",
            bg="#2563eb",
            bd=1,
            relief="raised",
            padx=6,
            pady=4,
        )
        self.fab.pack(fill="both", expand=True)

        self.fab.bind("<ButtonPress-1>", self.on_press)
        self.fab.bind("<B1-Motion>", self.on_drag)
        self.fab.bind("<ButtonRelease-1>", self.on_release)

        self.menu_win = None
        self.status_var = tk.StringVar(value="")
        self.wifi_info_var = tk.StringVar(value="Menyemak Wi-Fi...")
        self.wifi_buttons: list[tuple[dict, tk.Button]] = []

        self.keep_on_top()

    def keep_on_top(self):
        try:
            self.root.lift()
            if self.menu_win is not None and self.menu_win.winfo_exists():
                self.menu_win.lift()
        except Exception:
            pass
        self.root.after(self.keep_on_top_ms, self.keep_on_top)

    def on_press(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._moved = False

    def on_drag(self, event):
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        if abs(dx) > 5 or abs(dy) > 5:
            self._moved = True
            self.pos_x = max(0, min(self.screen_w - self.btn_w, self.pos_x + dx))
            self.pos_y = max(0, min(self.screen_h - self.btn_h, self.pos_y + dy))
            self.root.geometry(f"{self.btn_w}x{self.btn_h}+{self.pos_x}+{self.pos_y}")
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root

    def on_release(self, _event):
        if not self._moved:
            self.toggle_menu()

    def toggle_menu(self):
        if self.menu_win is not None and self.menu_win.winfo_exists():
            self.close_menu()
        else:
            self.open_menu()

    def close_menu(self):
        if self.menu_win is not None and self.menu_win.winfo_exists():
            self.menu_win.destroy()
        self.menu_win = None

    def open_menu(self):
        self.close_menu()
        self.menu_win = tk.Toplevel(self.root)
        self.menu_win.overrideredirect(True)
        self.menu_win.attributes("-topmost", True)
        self.menu_win.configure(bg="#1e293b", bd=2, relief="ridge")

        wifi_rows = max(1, (len(self.wifi_profiles) + 1) // 2)
        base_h = 276 + max(0, wifi_rows - 1) * 42
        mw = min(380, max(280, self.screen_w - 20))
        mh = min(self.screen_h - 10, base_h)
        mx = max(0, (self.screen_w - mw) // 2)
        my = max(0, (self.screen_h - mh) // 2)
        self.menu_win.geometry(f"{mw}x{mh}+{mx}+{my}")

        # Header
        header = tk.Frame(self.menu_win, bg="#0f172a", height=36)
        header.pack(fill="x")

        tk.Label(
            header,
            text=str(self.config.get("title", "KAWALAN SISTEM & WI-FI")),
            font=("Sans", 10, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
            padx=10,
            pady=6,
        ).pack(side="left")

        close_btn = tk.Button(
            header,
            text="✕ Tutup",
            font=("Sans", 9, "bold"),
            fg="#ffffff",
            bg="#475569",
            activebackground="#64748b",
            activeforeground="#ffffff",
            bd=0,
            padx=10,
            pady=4,
            command=self.close_menu,
        )
        close_btn.pack(side="right", padx=6, pady=4)

        body = tk.Frame(self.menu_win, bg="#1e293b", padx=12, pady=8)
        body.pack(fill="both", expand=True)

        # Paparan Wi-Fi Semasa
        tk.Label(
            body,
            textvariable=self.wifi_info_var,
            font=("Sans", 9, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        # Bahagian Pilih Wi-Fi
        tk.Label(
            body,
            text="Pilih Rangkaian Wi-Fi:",
            font=("Sans", 8),
            fg="#cbd5e1",
            bg="#1e293b",
            anchor="w",
        ).pack(fill="x")

        wifi_frame = tk.Frame(body, bg="#1e293b")
        wifi_frame.pack(fill="x", pady=4)

        self.wifi_buttons = []
        if not self.wifi_profiles:
            tk.Label(
                wifi_frame,
                text="Tiada profil Wi-Fi ditetapkan.\nJalankan ./setup-wifi.sh melalui SSH.",
                font=("Sans", 8),
                fg="#fbbf24",
                bg="#334155",
                pady=8,
                padx=8,
            ).pack(fill="x")
        else:
            cols = 1 if len(self.wifi_profiles) == 1 else 2
            for col in range(cols):
                wifi_frame.grid_columnconfigure(col, weight=1)

            for idx, wf in enumerate(self.wifi_profiles):
                row = idx // cols
                col = idx % cols
                btn = tk.Button(
                    wifi_frame,
                    text=f"📶 {wf['label']}",
                    font=("Sans", 9, "bold"),
                    fg="#ffffff",
                    bg="#334155",
                    activebackground="#2563eb",
                    activeforeground="#ffffff",
                    bd=1,
                    relief="raised",
                    pady=8,
                    command=lambda p=wf: self.switch_wifi(p),
                )
                padx = (0, 0) if cols == 1 else ((0, 4) if col == 0 else (4, 0))
                pady = (0, 4) if row < wifi_rows - 1 else (0, 0)
                btn.grid(row=row, column=col, sticky="ew", padx=padx, pady=pady)
                self.wifi_buttons.append((wf, btn))

        # Status mesej
        self.status_var.set("")
        self.status_label = tk.Label(
            body,
            textvariable=self.status_var,
            font=("Sans", 8, "bold"),
            fg="#fde047",
            bg="#1e293b",
            height=1,
        )
        self.status_label.pack(fill="x", pady=(2, 4))

        # Ruang tindakan kuasa (Power) atau pengesahan
        self.action_container = tk.Frame(body, bg="#1e293b")
        self.action_container.pack(fill="x", pady=(4, 0))

        self.show_power_buttons()
        self.refresh_wifi_status()

    def show_power_buttons(self):
        for child in self.action_container.winfo_children():
            child.destroy()

        tk.Label(
            self.action_container,
            text="Kawalan Kuasa Raspberry Pi:",
            font=("Sans", 8),
            fg="#cbd5e1",
            bg="#1e293b",
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        pwr_row = tk.Frame(self.action_container, bg="#1e293b")
        pwr_row.pack(fill="x")

        restart_btn = tk.Button(
            pwr_row,
            text="🔄 Restart",
            font=("Sans", 10, "bold"),
            fg="#ffffff",
            bg="#d97706",
            activebackground="#b45309",
            activeforeground="#ffffff",
            bd=1,
            relief="raised",
            pady=10,
            command=lambda: self.confirm_power("restart"),
        )
        restart_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        shutdown_btn = tk.Button(
            pwr_row,
            text="⏻ Shutdown",
            font=("Sans", 10, "bold"),
            fg="#ffffff",
            bg="#dc2626",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            bd=1,
            relief="raised",
            pady=10,
            command=lambda: self.confirm_power("shutdown"),
        )
        shutdown_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        pwr_row.grid_columnconfigure(0, weight=1)
        pwr_row.grid_columnconfigure(1, weight=1)

    def confirm_power(self, mode: str):
        for child in self.action_container.winfo_children():
            child.destroy()

        title = "Pasti mahu RESTART sekarang?" if mode == "restart" else "Pasti mahu SHUTDOWN sekarang?"
        color = "#d97706" if mode == "restart" else "#dc2626"

        tk.Label(
            self.action_container,
            text=title,
            font=("Sans", 9, "bold"),
            fg="#fef08a",
            bg="#1e293b",
        ).pack(fill="x", pady=(0, 4))

        row = tk.Frame(self.action_container, bg="#1e293b")
        row.pack(fill="x")

        yes_btn = tk.Button(
            row,
            text=f"Ya, {mode.capitalize()}",
            font=("Sans", 10, "bold"),
            fg="#ffffff",
            bg=color,
            activebackground=color,
            activeforeground="#ffffff",
            pady=10,
            command=lambda: self.execute_power(mode),
        )
        yes_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        cancel_btn = tk.Button(
            row,
            text="Batal",
            font=("Sans", 10, "bold"),
            fg="#ffffff",
            bg="#475569",
            activebackground="#64748b",
            activeforeground="#ffffff",
            pady=10,
            command=self.show_power_buttons,
        )
        cancel_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)

    def execute_power(self, mode: str):
        self.status_var.set("Sedang memproses arahan kuasa...")
        cmd = ["systemctl", "reboot"] if mode == "restart" else ["systemctl", "poweroff"]

        def worker():
            res = run_privileged(cmd, timeout=10)
            if res.returncode != 0:
                err = (res.stderr or "Tiada kebenaran").strip().splitlines()[0]
                self.root.after(0, lambda: self.status_var.set(f"Gagal: {err}"))

        threading.Thread(target=worker, daemon=True).start()

    def refresh_wifi_status(self):
        def worker():
            ssid, ip_addr = get_current_wifi_and_ip(self.wifi_interface)
            self.root.after(0, lambda: self._update_wifi_ui(ssid, ip_addr))

        threading.Thread(target=worker, daemon=True).start()

    def _update_wifi_ui(self, ssid: str, ip_addr: str):
        self.wifi_info_var.set(f"Wi-Fi Aktif: {ssid} ({ip_addr})")
        for wf, btn in self.wifi_buttons:
            if not btn.winfo_exists():
                continue
            if wf["ssid"] == ssid:
                btn.configure(bg="#16a34a", text=f"✓ {wf['label']}")
            else:
                btn.configure(bg="#334155", text=f"📶 {wf['label']}")

    def switch_wifi(self, profile: dict):
        target_label = profile["label"]
        con_name = profile["con_name"]
        self.status_var.set(f"Menyambung ke {target_label}...")

        def worker():
            try:
                # Set keutamaan autoconnect supaya pilihan kekal selepas reboot
                for wf in self.wifi_profiles:
                    prio = "10" if wf["con_name"] == con_name else "5"
                    run_privileged(
                        [
                            "nmcli",
                            "connection",
                            "modify",
                            wf["con_name"],
                            "connection.autoconnect-priority",
                            prio,
                        ],
                        timeout=5,
                    )

                run_privileged(
                    ["nmcli", "device", "wifi", "rescan", "ifname", self.wifi_interface],
                    timeout=5,
                )
                res = run_privileged(
                    ["nmcli", "--wait", "15", "connection", "up", con_name],
                    timeout=20,
                )
                ssid, ip_addr = get_current_wifi_and_ip(self.wifi_interface)
                if res.returncode == 0 and ssid == profile["ssid"]:
                    msg = f"Berjaya disambung ke {target_label}!"
                else:
                    msg = f"Gagal sambung ke {target_label} (tiada liputan?)"
            except Exception as exc:
                ssid, ip_addr = get_current_wifi_and_ip(self.wifi_interface)
                msg = f"Ralat sambungan: {exc}"

            def done():
                self.status_var.set(msg)
                self._update_wifi_ui(ssid, ip_addr)

            self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


def parse_args():
    parser = argparse.ArgumentParser(description="RasPi Hunter Floating Menu (Wi-Fi & Kawalan Sistem)")
    parser.add_argument(
        "-c",
        "--config",
        help="Laluan ke fail config.json (pilihan)",
        default=None,
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)
    app_root = tk.Tk()
    RasPiHunterFloatingMenu(app_root, config)
    app_root.mainloop()


if __name__ == "__main__":
    main()
