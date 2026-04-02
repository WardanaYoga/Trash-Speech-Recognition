"""
================================================================
  GUI Python – ESP32 Servo Controller via Bluetooth
  ------------------------------------------------
  Kontrol servo pemilah sampah melalui koneksi Bluetooth Serial.

  Instalasi dependensi:
    pip install pyserial

  Cara pairing Bluetooth (Windows):
    1. Nyalakan ESP32
    2. Buka Settings → Bluetooth → Add Device
    3. Pilih "ESP32_SampahSorter" (PIN: 1234)
    4. Setelah paired, cek COM port di Device Manager
       (biasanya COM3, COM4, dll.)
    5. Masukkan COM port tersebut di aplikasi ini

  Cara pairing Bluetooth (Linux):
    rfcomm bind 0 <MAC_ADDRESS>
    Port menjadi: /dev/rfcomm0
================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading
import time
from datetime import datetime


# ── Konstanta Warna & Font ─────────────────────────────────────
BG_DARK      = "#0F1923"
BG_CARD      = "#162030"
BG_INPUT     = "#1E2D3D"
ACCENT_GREEN = "#00E676"
ACCENT_BLUE  = "#29B6F6"
ACCENT_RED   = "#FF5252"
ACCENT_AMBER = "#FFD740"
TEXT_PRIMARY = "#E8F0F7"
TEXT_MUTED   = "#607D8B"
BORDER_COLOR = "#263545"

FONT_TITLE   = ("Segoe UI", 22, "bold")
FONT_LABEL   = ("Segoe UI", 10)
FONT_BUTTON  = ("Segoe UI", 12, "bold")
FONT_MONO    = ("Consolas", 9)
FONT_STATUS  = ("Segoe UI", 10, "bold")


class ServoControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🗑️  ESP32 Sampah Sorter – Servo Controller")
        self.root.geometry("700x680")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, False)

        self.serial_conn  = None
        self.is_connected = False
        self.read_thread  = None
        self.running      = False
        self.current_pos  = "default"  # Lacak posisi servo

        self._build_ui()
        self._refresh_ports()

    # ── Bangun UI ──────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self.root, bg=BG_DARK, pady=16)
        header.pack(fill="x", padx=24)

        tk.Label(header, text="🗑️  Sampah Sorter",
                 font=FONT_TITLE, bg=BG_DARK,
                 fg=ACCENT_GREEN).pack(side="left")

        self.conn_badge = tk.Label(header, text="● DISCONNECTED",
                                   font=("Segoe UI", 9, "bold"),
                                   bg=BG_DARK, fg=ACCENT_RED)
        self.conn_badge.pack(side="right", padx=4)

        # ── Separator ──
        tk.Frame(self.root, bg=BORDER_COLOR, height=1).pack(fill="x", padx=24)

        # ── Card Koneksi ──
        conn_card = tk.Frame(self.root, bg=BG_CARD,
                              relief="flat", bd=0, pady=16)
        conn_card.pack(fill="x", padx=24, pady=(14, 0))

        tk.Label(conn_card, text="KONEKSI BLUETOOTH",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", padx=16)

        row1 = tk.Frame(conn_card, bg=BG_CARD)
        row1.pack(fill="x", padx=16, pady=(6, 0))

        tk.Label(row1, text="COM Port:", font=FONT_LABEL,
                 bg=BG_CARD, fg=TEXT_PRIMARY, width=10,
                 anchor="w").grid(row=0, column=0, padx=(0, 8))

        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(row1, textvariable=self.port_var,
                                        width=18, state="readonly",
                                        font=FONT_LABEL)
        self.port_combo.grid(row=0, column=1)
        self._style_combobox()

        tk.Label(row1, text="Baud Rate:", font=FONT_LABEL,
                 bg=BG_CARD, fg=TEXT_PRIMARY, width=10,
                 anchor="w").grid(row=0, column=2, padx=(20, 8))

        self.baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(row1, textvariable=self.baud_var,
                                   values=["9600", "115200"],
                                   width=10, state="readonly",
                                   font=FONT_LABEL)
        baud_combo.grid(row=0, column=3)

        row2 = tk.Frame(conn_card, bg=BG_CARD)
        row2.pack(fill="x", padx=16, pady=(10, 4))

        self.btn_refresh = self._small_btn(row2, "🔄 Refresh",
                                            ACCENT_BLUE, self._refresh_ports)
        self.btn_refresh.pack(side="left", padx=(0, 8))

        self.btn_connect = self._small_btn(row2, "🔗 Connect",
                                            ACCENT_GREEN, self._toggle_connection)
        self.btn_connect.pack(side="left")

        # ── Card Visualisasi Servo ──
        servo_card = tk.Frame(self.root, bg=BG_CARD, pady=16)
        servo_card.pack(fill="x", padx=24, pady=(12, 0))

        tk.Label(servo_card, text="POSISI SERVO",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", padx=16)

        self.canvas = tk.Canvas(servo_card, width=640, height=90,
                                 bg=BG_INPUT, highlightthickness=0)
        self.canvas.pack(padx=16, pady=(8, 4))
        self._draw_servo_visual("default")

        # ── Card Tombol Kontrol ──
        ctrl_card = tk.Frame(self.root, bg=BG_CARD, pady=16)
        ctrl_card.pack(fill="x", padx=24, pady=(12, 0))

        tk.Label(ctrl_card, text="KONTROL SERVO",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", padx=16)

        btn_row = tk.Frame(ctrl_card, bg=BG_CARD)
        btn_row.pack(pady=(10, 4))

        self.btn_anorganik = self._ctrl_btn(
            btn_row, "◀  ANORGANIK\n(Kiri  •  180°)",
            ACCENT_BLUE, lambda: self._send_command("anorganik"))
        self.btn_anorganik.pack(side="left", padx=10)

        self.btn_default = self._ctrl_btn(
            btn_row, "●  DEFAULT\n(Tengah  •  90°)",
            ACCENT_AMBER, lambda: self._send_command("default"))
        self.btn_default.pack(side="left", padx=10)

        self.btn_organik = self._ctrl_btn(
            btn_row, "ORGANIK  ▶\n(Kanan  •  0°)",
            ACCENT_GREEN, lambda: self._send_command("organik"))
        self.btn_organik.pack(side="left", padx=10)

        # ── Status ──
        status_row = tk.Frame(self.root, bg=BG_DARK)
        status_row.pack(fill="x", padx=24, pady=(10, 0))

        tk.Label(status_row, text="STATUS  ", font=FONT_STATUS,
                 bg=BG_DARK, fg=TEXT_MUTED).pack(side="left")
        self.lbl_status = tk.Label(status_row, text="Belum terhubung.",
                                    font=FONT_STATUS, bg=BG_DARK,
                                    fg=TEXT_MUTED)
        self.lbl_status.pack(side="left")

        # ── Log Terminal ──
        log_card = tk.Frame(self.root, bg=BG_CARD, pady=10)
        log_card.pack(fill="both", expand=True, padx=24, pady=(10, 16))

        log_header = tk.Frame(log_card, bg=BG_CARD)
        log_header.pack(fill="x", padx=12)
        tk.Label(log_header, text="TERMINAL LOG",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(side="left")
        self._small_btn(log_header, "Bersihkan",
                         TEXT_MUTED, self._clear_log,
                         small=True).pack(side="right")

        self.log_text = scrolledtext.ScrolledText(
            log_card, width=80, height=8,
            bg=BG_INPUT, fg=ACCENT_GREEN,
            font=FONT_MONO, relief="flat",
            insertbackground=ACCENT_GREEN,
            selectbackground=BORDER_COLOR)
        self.log_text.pack(fill="both", expand=True,
                            padx=12, pady=(6, 0))
        self.log_text.configure(state="disabled")

        # ── Disable tombol kontrol awal ──
        self._set_control_state(False)

    # ── Widget Helpers ─────────────────────────────────────────
    def _ctrl_btn(self, parent, text, color, cmd):
        btn = tk.Button(parent, text=text, font=FONT_BUTTON,
                        bg=BG_INPUT, fg=color,
                        activebackground=color,
                        activeforeground=BG_DARK,
                        relief="flat", cursor="hand2",
                        width=15, height=3,
                        bd=0, highlightthickness=1,
                        highlightbackground=color,
                        command=cmd)
        return btn

    def _small_btn(self, parent, text, color, cmd, small=False):
        f = ("Segoe UI", 8) if small else ("Segoe UI", 10)
        btn = tk.Button(parent, text=text, font=f,
                        bg=BG_INPUT, fg=color,
                        activebackground=color,
                        activeforeground=BG_DARK,
                        relief="flat", cursor="hand2",
                        padx=10, pady=4,
                        bd=0, command=cmd)
        return btn

    def _style_combobox(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                         fieldbackground=BG_INPUT,
                         background=BG_INPUT,
                         foreground=TEXT_PRIMARY,
                         selectbackground=BORDER_COLOR)

    # ── Visualisasi Servo di Canvas ────────────────────────────
    def _draw_servo_visual(self, position):
        c = self.canvas
        c.delete("all")

        w, h = 640, 90
        track_y = h // 2
        margin  = 80

        # Track bar
        c.create_line(margin, track_y, w - margin, track_y,
                      fill=BORDER_COLOR, width=3)

        # Label posisi
        positions = {
            "anorganik": (margin,          "KIRI\n180°",  ACCENT_BLUE),
            "default":   (w // 2,          "TENGAH\n90°", ACCENT_AMBER),
            "organik":   (w - margin,      "KANAN\n0°",   ACCENT_GREEN),
        }

        for key, (x, label, color) in positions.items():
            is_active = (key == position)
            dot_r     = 10 if is_active else 6
            dot_color = color if is_active else BORDER_COLOR

            c.create_oval(x - dot_r, track_y - dot_r,
                          x + dot_r, track_y + dot_r,
                          fill=dot_color, outline="")

            lbl_y = track_y - 28 if is_active else track_y - 22
            lbl_f = ("Segoe UI", 8, "bold") if is_active \
                    else ("Segoe UI", 7)
            c.create_text(x, lbl_y, text=label,
                           font=lbl_f,
                           fill=color if is_active else TEXT_MUTED,
                           justify="center")

        # Servo body
        active_x = positions[position][0]
        c.create_rectangle(active_x - 20, track_y - 8,
                            active_x + 20, track_y + 8,
                            fill=positions[position][2],
                            outline="", tags="servo_body")

        # Arrow indicator
        c.create_text(active_x, track_y + 24,
                      text=f"▲  {position.upper()}",
                      font=("Segoe UI", 8, "bold"),
                      fill=positions[position][2])

    # ── Koneksi Bluetooth ──────────────────────────────────────
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports:
            self.port_var.set(ports[0])
        self._log("🔄 Port di-refresh. Ditemukan: " +
                  (", ".join(ports) if ports else "tidak ada port"))

    def _toggle_connection(self):
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_var.get()
        baud = int(self.baud_var.get())

        if not port:
            messagebox.showwarning("Peringatan",
                                    "Pilih COM Port terlebih dahulu!")
            return
        try:
            self.serial_conn = serial.Serial(
                port, baud, timeout=1)
            self.is_connected = True
            self.running      = True

            # Update UI
            self.btn_connect.configure(text="🔌 Disconnect",
                                        fg=ACCENT_RED)
            self.conn_badge.configure(
                text=f"● CONNECTED  {port}",
                fg=ACCENT_GREEN)
            self._set_control_state(True)
            self._set_status(f"Terhubung ke {port} @ {baud} baud", ACCENT_GREEN)
            self._log(f"✅ Terhubung ke {port} dengan baud rate {baud}")

            # Mulai thread baca
            self.read_thread = threading.Thread(
                target=self._read_loop, daemon=True)
            self.read_thread.start()

        except serial.SerialException as e:
            messagebox.showerror("Gagal Konek",
                                  f"Tidak bisa membuka port {port}:\n{e}")
            self._log(f"❌ Gagal terhubung: {e}")

    def _disconnect(self):
        self.running      = False
        self.is_connected = False

        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

        self.btn_connect.configure(text="🔗 Connect", fg=ACCENT_GREEN)
        self.conn_badge.configure(text="● DISCONNECTED", fg=ACCENT_RED)
        self._set_control_state(False)
        self._set_status("Koneksi diputus.", TEXT_MUTED)
        self._log("🔌 Koneksi Bluetooth diputus.")

    # ── Baca Data dari ESP32 ───────────────────────────────────
    def _read_loop(self):
        while self.running and self.serial_conn.is_open:
            try:
                if self.serial_conn.in_waiting:
                    raw  = self.serial_conn.readline()
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if line:
                        self.root.after(0, self._handle_response, line)
            except serial.SerialException:
                self.root.after(0, self._on_disconnect_error)
                break
            except Exception:
                pass
            time.sleep(0.05)

    def _handle_response(self, line):
        self._log(f"◀ {line}")

        if line.startswith("OK:"):
            parts = line.split(":")
            cmd   = parts[1] if len(parts) > 1 else ""
            arah  = parts[2] if len(parts) > 2 else ""
            self.current_pos = cmd
            self._draw_servo_visual(cmd)
            self._set_status(
                f"Servo → {cmd.upper()} ({arah})", ACCENT_GREEN)

        elif line.startswith("STATUS:"):
            self._set_status(line.replace("STATUS:", ""), ACCENT_BLUE)

        elif line.startswith("ERROR:"):
            self._set_status(line, ACCENT_RED)

    def _on_disconnect_error(self):
        if self.is_connected:
            self._log("⚠️  Koneksi terputus tak terduga!")
            self._disconnect()

    # ── Kirim Perintah ────────────────────────────────────────
    def _send_command(self, cmd):
        if not self.is_connected or not self.serial_conn.is_open:
            messagebox.showwarning("Tidak Terhubung",
                                    "Hubungkan ke ESP32 terlebih dahulu!")
            return
        try:
            self.serial_conn.write(f"{cmd}\n".encode("utf-8"))
            self._log(f"▶ Dikirim: {cmd}")
        except serial.SerialException as e:
            self._log(f"❌ Gagal kirim: {e}")
            self._disconnect()

    # ── UI Helpers ─────────────────────────────────────────────
    def _set_control_state(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in [self.btn_organik,
                    self.btn_anorganik,
                    self.btn_default]:
            btn.configure(state=state)

    def _set_status(self, msg, color=TEXT_MUTED):
        self.lbl_status.configure(text=msg, fg=color)

    def _log(self, msg):
        ts  = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {msg}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ── Tutup Aplikasi ─────────────────────────────────────────
    def on_close(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.root.destroy()


# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = ServoControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
