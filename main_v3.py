"""
================================================================
  Smart Waste System — GUI Python v3
================================================================
  Perbaikan dari versi sebelumnya (main_v2.py):

  [1] Perintah serial dikirim DULU ke ESP32, baru audio diputar
      di thread terpisah → servo langsung gerak tanpa nunggu audio
  [2] Semua update UI dari background thread pakai root.after()
      → thread-safe, tidak crash
  [3] bare except: diganti exception spesifik per jenis error
      → WaitTimeoutError, UnknownValueError, RequestError, dll.
  [4] Serial port disimpan sebagai instance variable & ditutup
      dengan benar saat stop() / exit_app()
  [5] threading.Event() menggantikan global variable 'running'
      → sinkronisasi thread yang aman
  [6] Validasi file audio saat startup → pesan jelas kalau
      file tidak ditemukan, tidak crash diam-diam
  [7] Tunggu feedback "READY" dari ESP32 sebelum mulai listen
      → pastikan ESP32 benar-benar siap
  [8] Thread reader terpisah untuk baca response dari ESP32
      → log balasan ESP32 tampil real-time di UI

  Instalasi:
    pip install pyserial SpeechRecognition
================================================================
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import re
from pathlib import Path
from ctypes import windll

import speech_recognition as sr
import serial
from serial.tools import list_ports

# ── Konfigurasi ───────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
ORGANIK_AUDIO   = BASE_DIR / "Organik.mp3"
UNORGANIK_AUDIO = BASE_DIR / "Unorganik.mp3"
TUTUP_AUDIO     = BASE_DIR / "Tutup.mp3"
SERIAL_BAUDRATE = 115200


# ── Audio (Windows MCI) ───────────────────────────────────────
def _mci_send(command: str):
    windll.winmm.mciSendStringW(command, None, 0, None)

def play_feedback_mp3(mp3_path: Path):
    """Putar audio MP3 secara blocking (dipanggil di thread terpisah)."""
    alias = "feedback_audio"
    path  = str(mp3_path).replace('"', "")
    _mci_send(f"close {alias}")
    _mci_send(f'open "{path}" type mpegvideo alias {alias}')
    _mci_send(f"play {alias} wait")
    _mci_send(f"close {alias}")

def play_audio_async(mp3_path: Path):
    """[FIX-1] Putar audio di thread terpisah agar tidak block."""
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

def get_ports() -> list[str]:
    return [p.device for p in list_ports.comports()]

def send_command(ser: serial.Serial, result: str):
    """Kirim 1 byte perintah ke ESP32."""
    cmd_map = {"ORGANIK": b"0", "ANORGANIK": b"1", "TUTUP": b"2"}
    if result in cmd_map:
        ser.write(cmd_map[result])


# ── Aplikasi GUI ──────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root       = root
        self.root.title("Smart Waste System")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#0f172a")

        # [FIX-4] Serial sebagai instance variable
        self.ser: serial.Serial | None = None

        # [FIX-5] threading.Event gantikan global running
        self.stop_event = threading.Event()

        self.selected_port = tk.StringVar()
        self.status_text   = tk.StringVar(value="READY")
        self.detect_text   = tk.StringVar(value="-")

        self._build_ui()
        self._validate_audio_files()   # [FIX-6]
        self.refresh_ports()

    # ── Validasi file audio ───────────────────────────────────
    def _validate_audio_files(self):
        """[FIX-6] Cek file audio ada saat startup."""
        missing = []
        for path in [ORGANIK_AUDIO, UNORGANIK_AUDIO, TUTUP_AUDIO]:
            if not path.exists():
                missing.append(path.name)
        if missing:
            self.update_ui(
                f"⚠ FILE AUDIO TIDAK DITEMUKAN: {', '.join(missing)}",
                color="#f59e0b"
            )

    # ── Build UI ──────────────────────────────────────────────
    def _build_ui(self):
        tk.Label(self.root, text="SMART WASTE SYSTEM",
                 font=("Segoe UI", 40, "bold"),
                 fg="white", bg="#0f172a").pack(pady=30)

        # COM Select
        com_frame = tk.Frame(self.root, bg="#0f172a")
        com_frame.pack(pady=10)

        tk.Label(com_frame, text="PILIH COM:",
                 font=("Segoe UI", 14),
                 fg="white", bg="#0f172a").grid(row=0, column=0, padx=10)

        self.com_box = ttk.Combobox(
            com_frame, textvariable=self.selected_port,
            font=("Segoe UI", 12), width=15, state="readonly")
        self.com_box.grid(row=0, column=1, padx=10)

        tk.Button(com_frame, text="REFRESH",
                  command=self.refresh_ports,
                  bg="#38bdf8", fg="white").grid(row=0, column=2, padx=10)

        # Status label
        self.status_label = tk.Label(
            self.root, textvariable=self.status_text,
            font=("Segoe UI", 20), fg="#38bdf8", bg="#0f172a")
        self.status_label.pack(pady=10)

        # Result box
        self.result_box = tk.Label(
            self.root, textvariable=self.detect_text,
            font=("Segoe UI", 50, "bold"),
            width=20, height=2, bg="#1e293b", fg="white")
        self.result_box.pack(pady=30)

        # ESP32 response log
        log_frame = tk.Frame(self.root, bg="#0f172a")
        log_frame.pack(pady=4)
        tk.Label(log_frame, text="ESP32 Response:",
                 font=("Segoe UI", 11),
                 fg="#94a3b8", bg="#0f172a").pack(side="left")
        self.esp_log_var = tk.StringVar(value="-")
        tk.Label(log_frame, textvariable=self.esp_log_var,
                 font=("Consolas", 11), fg="#4ade80",
                 bg="#0f172a").pack(side="left", padx=8)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#0f172a")
        btn_frame.pack(pady=20)

        self.btn_start = tk.Button(
            btn_frame, text="START",
            font=("Segoe UI", 16, "bold"),
            bg="#22c55e", fg="white",
            width=10, command=self.start)
        self.btn_start.grid(row=0, column=0, padx=20)

        self.btn_stop = tk.Button(
            btn_frame, text="STOP",
            font=("Segoe UI", 16, "bold"),
            bg="#f59e0b", fg="white",
            width=10, command=self.stop,
            state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=20)

        tk.Button(btn_frame, text="EXIT",
                  font=("Segoe UI", 16, "bold"),
                  bg="#ef4444", fg="white",
                  width=10, command=self.exit_app).grid(
                  row=0, column=2, padx=20)

    # ── Update UI (thread-safe) ───────────────────────────────
    def update_ui(self, status: str = None, result: str = None,
                  color: str = None):
        """[FIX-2] Selalu pakai root.after() agar thread-safe."""
        def _do():
            if status is not None:
                self.status_text.set(status)
                self.status_label.config(
                    fg=color if color else "#38bdf8")

            if result is not None:
                self.detect_text.set(result)
                color_map = {
                    "ORGANIK":         "#22c55e",
                    "ANORGANIK":       "#ef4444",
                    "TIDAK DIKENALI":  "#64748b",
                }
                self.result_box.config(
                    bg=color_map.get(result, "#1e293b"))

        self.root.after(0, _do)

    def _update_esp_log(self, msg: str):
        """Update label response ESP32 dari thread manapun."""
        self.root.after(0, lambda: self.esp_log_var.set(msg))

    # ── Port ──────────────────────────────────────────────────
    def refresh_ports(self):
        ports = get_ports()
        self.com_box["values"] = ports
        if ports:
            self.com_box.current(0)

    # ── Start / Stop ──────────────────────────────────────────
    def start(self):
        if not self.selected_port.get():
            self.update_ui("⚠ PILIH COM PORT TERLEBIH DAHULU!")
            return

        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        threading.Thread(target=self._voice_loop,
                         daemon=True).start()

    def stop(self):
        """[FIX-4][FIX-5] Hentikan loop dan tutup serial."""
        self.stop_event.set()
        self._close_serial()
        self.update_ui("STOPPED", "-")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def exit_app(self):
        self.stop_event.set()
        self._close_serial()
        self.root.destroy()

    def _close_serial(self):
        """[FIX-4] Tutup serial port dengan aman."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except serial.SerialException:
                pass
        self.ser = None

    # ── Thread: baca response dari ESP32 ─────────────────────
    def _serial_reader(self):
        """[FIX-8] Thread terpisah baca feedback dari ESP32."""
        while not self.stop_event.is_set():
            try:
                if self.ser and self.ser.is_open and self.ser.in_waiting:
                    line = self.ser.readline().decode("utf-8",
                                                       errors="ignore").strip()
                    if line:
                        self._update_esp_log(line)
            except serial.SerialException:
                break
            except Exception:
                pass
            time.sleep(0.05)

    # ── Thread utama: voice recognition loop ─────────────────
    def _voice_loop(self):
        recognizer = sr.Recognizer()
        port       = self.selected_port.get()

        # Buka serial
        try:
            self.ser = serial.Serial(port, SERIAL_BAUDRATE, timeout=1)
            time.sleep(2)  # tunggu ESP32 reset setelah koneksi serial
        except serial.SerialException as e:
            self.update_ui(f"❌ GAGAL BUKA PORT: {e}", color="#ef4444")
            self.root.after(0, lambda: (
                self.btn_start.config(state="normal"),
                self.btn_stop.config(state="disabled")
            ))
            return

        # [FIX-7] Tunggu sinyal READY dari ESP32
        self.update_ui("⏳ MENUNGGU ESP32 SIAP...")
        ready_deadline = time.time() + 5  # maks 5 detik tunggu
        while time.time() < ready_deadline:
            if self.ser.in_waiting:
                line = self.ser.readline().decode(
                    "utf-8", errors="ignore").strip()
                if line == "READY":
                    break
            time.sleep(0.1)

        # Mulai reader thread
        threading.Thread(target=self._serial_reader,
                         daemon=True).start()

        self.update_ui("🎤 SISTEM AKTIF", color="#4ade80")

        # Loop pengenalan suara
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)

                while not self.stop_event.is_set():
                    try:
                        self.update_ui("👂 LISTENING...")

                        # [FIX-3] Tangkap timeout secara spesifik
                        try:
                            audio = recognizer.listen(
                                source, timeout=5, phrase_time_limit=4)
                        except sr.WaitTimeoutError:
                            # Tidak ada suara dalam 5 detik — normal, lanjut
                            continue

                        self.update_ui("⚙ MEMPROSES...")

                        try:
                            text   = recognizer.recognize_google(
                                audio, language="id-ID")
                            result = classify_text(text)
                        except sr.UnknownValueError:
                            # Suara tidak bisa dikenali
                            self.update_ui("🔇 SUARA TIDAK JELAS", "-")
                            continue
                        except sr.RequestError as e:
                            # Masalah koneksi ke Google API
                            self.update_ui(
                                f"🌐 ERROR API GOOGLE: {e}", "-",
                                color="#f59e0b")
                            continue

                        self.update_ui("✅ TERDETEKSI", result)

                        # [FIX-1] Kirim perintah DULU, audio BELAKANGAN
                        if result in ("ORGANIK", "ANORGANIK", "TUTUP"):
                            send_command(self.ser, result)

                        audio_map = {
                            "ORGANIK":   ORGANIK_AUDIO,
                            "ANORGANIK": UNORGANIK_AUDIO,
                            "TUTUP":     TUTUP_AUDIO,
                        }
                        if result in audio_map:
                            play_audio_async(audio_map[result])

                    except serial.SerialException as e:
                        self.update_ui(
                            f"❌ SERIAL ERROR: {e}", "-",
                            color="#ef4444")
                        break

        except Exception as e:
            self.update_ui(f"❌ ERROR: {e}", "-", color="#ef4444")

        finally:
            # [FIX-4] Pastikan serial ditutup ketika loop selesai
            self._close_serial()
            if not self.stop_event.is_set():
                # Loop berakhir karena error, bukan karena stop()
                self.root.after(0, lambda: (
                    self.btn_start.config(state="normal"),
                    self.btn_stop.config(state="disabled")
                ))


# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = App(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    root.mainloop()
