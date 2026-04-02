"""
================================================================
  Smart Waste System — GUI Python v4 (WiFi TCP)
================================================================
  Cara penggunaan:
    1. Upload esp32_wifi_ap.ino ke ESP32
    2. Hubungkan laptop/PC ke WiFi: ESP32_SAMPAH (pass: 12345678)
    3. Jalankan program ini → klik CONNECT → klik START

  Tidak perlu pilih COM port lagi.
  Komunikasi melalui TCP Socket ke 192.168.4.1:8080

  Instalasi:
    pip install SpeechRecognition pyaudio
================================================================
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import re
import socket
from pathlib import Path
from ctypes import windll

import speech_recognition as sr

# ── Konfigurasi ───────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
ORGANIK_AUDIO   = BASE_DIR / "Organik.mp3"
UNORGANIK_AUDIO = BASE_DIR / "Unorganik.mp3"
TUTUP_AUDIO     = BASE_DIR / "Tutup.mp3"

ESP32_IP        = "192.168.4.1"   # IP default AP ESP32 (jangan diubah)
ESP32_PORT      = 8080
SOCKET_TIMEOUT  = 5               # detik


# ── Audio (Windows MCI) ───────────────────────────────────────
def _mci_send(command: str):
    windll.winmm.mciSendStringW(command, None, 0, None)

def play_feedback_mp3(mp3_path: Path):
    alias = "feedback_audio"
    path  = str(mp3_path).replace('"', "")
    _mci_send(f"close {alias}")
    _mci_send(f'open "{path}" type mpegvideo alias {alias}')
    _mci_send(f"play {alias} wait")
    _mci_send(f"close {alias}")

def play_audio_async(mp3_path: Path):
    if mp3_path.exists():
        threading.Thread(
            target=play_feedback_mp3,
            args=(mp3_path,),
            daemon=True
        ).start()


# ── Klasifikasi suara ─────────────────────────────────────────
def classify_text(text: str) -> str:
    text = text.lower()
    if re.search(r"\b(anorganik|unorganik|non organik)\b", text):
        return "ANORGANIK"
    if re.search(r"\borganik\b", text):
        return "ORGANIK"
    if re.search(r"\btutup\b", text):
        return "TUTUP"
    return "TIDAK DIKENALI"


# ── Aplikasi GUI ──────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smart Waste System")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#0f172a")

        self.sock: socket.socket | None = None
        self.stop_event    = threading.Event()
        self.is_connected  = False

        self.status_text  = tk.StringVar(value="Belum terhubung ke ESP32")
        self.detect_text  = tk.StringVar(value="-")
        self.esp_log_var  = tk.StringVar(value="-")

        self._build_ui()
        self._validate_audio_files()

    # ── Validasi audio ────────────────────────────────────────
    def _validate_audio_files(self):
        missing = [p.name for p in
                   [ORGANIK_AUDIO, UNORGANIK_AUDIO, TUTUP_AUDIO]
                   if not p.exists()]
        if missing:
            self.update_ui(
                f"⚠ File audio tidak ditemukan: {', '.join(missing)}",
                color="#f59e0b")

    # ── Build UI ──────────────────────────────────────────────
    def _build_ui(self):
        # Title
        tk.Label(self.root, text="SMART WASTE SYSTEM",
                 font=("Segoe UI", 40, "bold"),
                 fg="white", bg="#0f172a").pack(pady=30)

        # Info koneksi WiFi
        info_frame = tk.Frame(self.root, bg="#1e293b",
                               padx=20, pady=12)
        info_frame.pack(pady=(0, 10))

        tk.Label(info_frame,
                 text="📶  Hubungkan laptop ke WiFi:",
                 font=("Segoe UI", 13), fg="#94a3b8",
                 bg="#1e293b").grid(row=0, column=0,
                                    columnspan=3, sticky="w")

        self._info_row(info_frame, 1, "SSID",     "ESP32_SAMPAH")
        self._info_row(info_frame, 2, "Password", "12345678")
        self._info_row(info_frame, 3, "IP ESP32", f"{ESP32_IP}:{ESP32_PORT}")

        # Tombol connect
        conn_row = tk.Frame(self.root, bg="#0f172a")
        conn_row.pack(pady=6)

        self.btn_connect = tk.Button(
            conn_row, text="🔗  CONNECT KE ESP32",
            font=("Segoe UI", 13, "bold"),
            bg="#38bdf8", fg="#0f172a",
            padx=20, pady=6,
            relief="flat", cursor="hand2",
            command=self.toggle_connect)
        self.btn_connect.pack()

        # Status
        self.status_label = tk.Label(
            self.root, textvariable=self.status_text,
            font=("Segoe UI", 18),
            fg="#38bdf8", bg="#0f172a",
            wraplength=1100, justify="center")
        self.status_label.pack(pady=8)

        # Result box
        self.result_box = tk.Label(
            self.root, textvariable=self.detect_text,
            font=("Segoe UI", 50, "bold"),
            width=20, height=2,
            bg="#1e293b", fg="white")
        self.result_box.pack(pady=20)

        # ESP32 log
        log_row = tk.Frame(self.root, bg="#0f172a")
        log_row.pack(pady=2)
        tk.Label(log_row, text="ESP32 Response:",
                 font=("Segoe UI", 11),
                 fg="#94a3b8", bg="#0f172a").pack(side="left")
        tk.Label(log_row, textvariable=self.esp_log_var,
                 font=("Consolas", 11),
                 fg="#4ade80", bg="#0f172a").pack(side="left", padx=8)

        # Control buttons
        btn_frame = tk.Frame(self.root, bg="#0f172a")
        btn_frame.pack(pady=20)

        self.btn_start = tk.Button(
            btn_frame, text="START",
            font=("Segoe UI", 16, "bold"),
            bg="#22c55e", fg="white",
            width=10, state="disabled",
            command=self.start)
        self.btn_start.grid(row=0, column=0, padx=20)

        self.btn_stop = tk.Button(
            btn_frame, text="STOP",
            font=("Segoe UI", 16, "bold"),
            bg="#f59e0b", fg="white",
            width=10, state="disabled",
            command=self.stop)
        self.btn_stop.grid(row=0, column=1, padx=20)

        tk.Button(btn_frame, text="EXIT",
                  font=("Segoe UI", 16, "bold"),
                  bg="#ef4444", fg="white",
                  width=10, command=self.exit_app
                  ).grid(row=0, column=2, padx=20)

    def _info_row(self, parent, row, label, value):
        tk.Label(parent, text=f"  {label}:",
                 font=("Segoe UI", 12), fg="#94a3b8",
                 bg="#1e293b", width=12,
                 anchor="w").grid(row=row, column=0, sticky="w", pady=1)
        tk.Label(parent, text=value,
                 font=("Segoe UI", 12, "bold"),
                 fg="white", bg="#1e293b").grid(
                 row=row, column=1, sticky="w", padx=8)

    # ── Update UI (thread-safe) ───────────────────────────────
    def update_ui(self, status: str = None, result: str = None,
                  color: str = None):
        def _do():
            if status is not None:
                self.status_text.set(status)
                self.status_label.config(
                    fg=color if color else "#38bdf8")
            if result is not None:
                self.detect_text.set(result)
                color_map = {
                    "ORGANIK":        "#22c55e",
                    "ANORGANIK":      "#ef4444",
                    "TIDAK DIKENALI": "#64748b",
                }
                self.result_box.config(
                    bg=color_map.get(result, "#1e293b"))
        self.root.after(0, _do)

    def _update_esp_log(self, msg: str):
        self.root.after(0, lambda: self.esp_log_var.set(msg))

    # ── Koneksi WiFi TCP ──────────────────────────────────────
    def toggle_connect(self):
        if self.is_connected:
            self._disconnect()
        else:
            threading.Thread(target=self._connect,
                             daemon=True).start()

    def _connect(self):
        self.update_ui("⏳ Menghubungkan ke ESP32...", color="#f59e0b")
        self.root.after(0, lambda: self.btn_connect.config(
            state="disabled"))
        try:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(SOCKET_TIMEOUT)
            self.sock.connect((ESP32_IP, ESP32_PORT))
            self.sock.settimeout(None)  # non-timeout setelah konek

            self.is_connected = True
            self.update_ui(
                f"✅ Terhubung ke {ESP32_IP}:{ESP32_PORT}",
                color="#4ade80")
            self.root.after(0, lambda: (
                self.btn_connect.config(
                    text="🔌  DISCONNECT", state="normal",
                    bg="#ef4444"),
                self.btn_start.config(state="normal")
            ))

            # Mulai reader thread
            threading.Thread(target=self._socket_reader,
                             daemon=True).start()

        except (ConnectionRefusedError, socket.timeout,
                OSError) as e:
            self.update_ui(
                f"❌ Gagal konek: {e}\n"
                "Pastikan laptop terhubung ke WiFi ESP32_SAMPAH",
                color="#ef4444")
            self.root.after(0, lambda: self.btn_connect.config(
                state="normal"))
            if self.sock:
                self.sock.close()
                self.sock = None

    def _disconnect(self):
        self.stop_event.set()
        self.is_connected = False
        self._close_socket()
        self.update_ui("🔌 Terputus dari ESP32.", color="#94a3b8")
        self.root.after(0, lambda: (
            self.btn_connect.config(
                text="🔗  CONNECT KE ESP32",
                state="normal", bg="#38bdf8"),
            self.btn_start.config(state="disabled"),
            self.btn_stop.config(state="disabled")
        ))

    def _close_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    # ── Thread: baca response dari ESP32 ─────────────────────
    def _socket_reader(self):
        buffer = ""
        while self.is_connected:
            try:
                self.sock.settimeout(1)
                chunk = self.sock.recv(256).decode(
                    "utf-8", errors="ignore")
                if not chunk:
                    # Koneksi ditutup oleh ESP32
                    break
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._update_esp_log(line)
            except socket.timeout:
                continue
            except OSError:
                break

        if self.is_connected:
            # Putus tak terduga
            self.update_ui("⚠ Koneksi ke ESP32 terputus!",
                           color="#ef4444")
            self._disconnect()

    # ── Kirim perintah ke ESP32 ───────────────────────────────
    def send_command(self, cmd_byte: bytes):
        if self.sock and self.is_connected:
            try:
                self.sock.sendall(cmd_byte)
            except OSError as e:
                self.update_ui(f"❌ Gagal kirim: {e}",
                               color="#ef4444")

    # ── Start / Stop voice ────────────────────────────────────
    def start(self):
        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_connect.config(state="disabled")
        threading.Thread(target=self._voice_loop,
                         daemon=True).start()

    def stop(self):
        self.stop_event.set()
        self.update_ui("⏹ Dihentikan.", "-", color="#94a3b8")
        self.root.after(0, lambda: (
            self.btn_start.config(state="normal"),
            self.btn_stop.config(state="disabled"),
            self.btn_connect.config(state="normal")
        ))

    def exit_app(self):
        self.stop_event.set()
        self.is_connected = False
        self._close_socket()
        self.root.destroy()

    # ── Thread: voice recognition ─────────────────────────────
    def _voice_loop(self):
        recognizer = sr.Recognizer()

        audio_map = {
            "ORGANIK":   ORGANIK_AUDIO,
            "ANORGANIK": UNORGANIK_AUDIO,
            "TUTUP":     TUTUP_AUDIO,
        }
        cmd_map = {
            "ORGANIK":   b"0",
            "ANORGANIK": b"1",
            "TUTUP":     b"2",
        }

        try:
            with sr.Microphone() as source:
                self.update_ui("🎙 Kalibrasi mikrofon...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                self.update_ui("🎤 SISTEM AKTIF — Siap mendengarkan",
                               color="#4ade80")

                while not self.stop_event.is_set():
                    try:
                        self.update_ui("👂 LISTENING...")
                        try:
                            audio = recognizer.listen(
                                source, timeout=5,
                                phrase_time_limit=4)
                        except sr.WaitTimeoutError:
                            continue

                        self.update_ui("⚙ Memproses...")

                        try:
                            text   = recognizer.recognize_google(
                                audio, language="id-ID")
                            result = classify_text(text)
                        except sr.UnknownValueError:
                            self.update_ui("🔇 Suara tidak jelas", "-")
                            continue
                        except sr.RequestError as e:
                            self.update_ui(
                                f"🌐 Error API Google: {e}", "-",
                                color="#f59e0b")
                            continue

                        self.update_ui("✅ Terdeteksi", result)

                        # Kirim ke ESP32 DULU
                        if result in cmd_map:
                            self.send_command(cmd_map[result])

                        # Audio diputar di thread terpisah
                        if result in audio_map:
                            play_audio_async(audio_map[result])

                    except Exception as e:
                        self.update_ui(f"❌ Error: {e}", "-",
                                       color="#ef4444")

        except Exception as e:
            self.update_ui(f"❌ Mikrofon error: {e}", "-",
                           color="#ef4444")
        finally:
            self.root.after(0, lambda: (
                self.btn_start.config(state="normal"),
                self.btn_stop.config(state="disabled"),
                self.btn_connect.config(state="normal")
            ))


# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = App(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    root.mainloop()
