import tkinter as tk
from tkinter import ttk
import threading
import time
import re
import socket
from pathlib import Path
from ctypes import windll

import speech_recognition as sr

# ================= CONFIG =================
BASE_DIR = Path(__file__).resolve().parent
ORGANIK_AUDIO   = BASE_DIR / "Organik.mp3"
UNORGANIK_AUDIO = BASE_DIR / "Unorganik.mp3"
TUTUP_AUDIO     = BASE_DIR / "Tutup.mp3"

ESP32_IP   = "192.168.4.1"   # IP default ESP32 Access Point
ESP32_PORT = 8080
running    = False

# ================= AUDIO =================
def _mci_send(command: str):
    windll.winmm.mciSendStringW(command, None, 0, None)

def play_feedback_mp3(mp3_path: Path):
    alias = "audio"
    path = str(mp3_path).replace('"', "")
    _mci_send(f"close {alias}")
    _mci_send(f'open "{path}" type mpegvideo alias {alias}')
    _mci_send(f"play {alias} wait")
    _mci_send(f"close {alias}")

# ================= LOGIC =================
def classify_text(text: str) -> str:
    text = text.lower()
    if re.search(r"\b(anorganik|unorganik|non organik)\b", text):
        return "ANORGANIK"
    if re.search(r"\borganik\b", text):
        return "ORGANIK"
    if re.search(r"\btutup\b", text):
        return "TUTUP"
    return "TIDAK DIKENALI"

def send_command(sock: socket.socket, result: str):
    try:
        if result == "ORGANIK":
            print("Kirim: 0")
            sock.sendall(b"0")
        elif result == "ANORGANIK":
            print("Kirim: 1")
            sock.sendall(b"1")
        elif result == "TUTUP":
            print("Kirim: 2")
            sock.sendall(b"2")
    except Exception as e:
        print("Socket error:", e)

# ================= GUI =================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Waste System")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#0f172a")

        self.sock: socket.socket | None = None
        self.status_text = tk.StringVar(value="READY")
        self.detect_text = tk.StringVar(value="-")

        # TITLE
        tk.Label(root, text="SMART WASTE SYSTEM",
                 font=("Segoe UI", 40, "bold"),
                 fg="white", bg="#0f172a").pack(pady=30)

        # === INFO WIFI ===
        wifi_frame = tk.Frame(root, bg="#1e293b", padx=20, pady=10)
        wifi_frame.pack(pady=5)

        tk.Label(wifi_frame,
                 text=f"📶  Hubungkan laptop ke WiFi  →  SSID: ESP32_SAMPAH   |   Password: 12345678   |   IP: {ESP32_IP}:{ESP32_PORT}",
                 font=("Segoe UI", 12),
                 fg="#94a3b8", bg="#1e293b").pack()

        # === TOMBOL CONNECT ===
        self.btn_connect = tk.Button(root,
                                     text="🔗  CONNECT KE ESP32",
                                     font=("Segoe UI", 14, "bold"),
                                     bg="#38bdf8", fg="#0f172a",
                                     padx=20, pady=6,
                                     relief="flat", cursor="hand2",
                                     command=self.toggle_connect)
        self.btn_connect.pack(pady=10)

        # STATUS
        self.status_label = tk.Label(root,
                                     textvariable=self.status_text,
                                     font=("Segoe UI", 20),
                                     fg="#38bdf8", bg="#0f172a",
                                     wraplength=1100)
        self.status_label.pack(pady=10)

        # RESULT BOX
        self.result_box = tk.Label(root,
                                   textvariable=self.detect_text,
                                   font=("Segoe UI", 50, "bold"),
                                   width=20, height=2,
                                   bg="#1e293b", fg="white")
        self.result_box.pack(pady=30)

        # BUTTONS
        frame = tk.Frame(root, bg="#0f172a")
        frame.pack(pady=20)

        self.btn_start = tk.Button(frame, text="START",
                                   font=("Segoe UI", 16, "bold"),
                                   bg="#22c55e", fg="white",
                                   width=10, state="disabled",
                                   command=self.start)
        self.btn_start.grid(row=0, column=0, padx=20)

        self.btn_stop = tk.Button(frame, text="STOP",
                                  font=("Segoe UI", 16, "bold"),
                                  bg="#f59e0b", fg="white",
                                  width=10, state="disabled",
                                  command=self.stop)
        self.btn_stop.grid(row=0, column=1, padx=20)

        tk.Button(frame, text="EXIT",
                  font=("Segoe UI", 16, "bold"),
                  bg="#ef4444", fg="white",
                  width=10, command=self.exit_app).grid(row=0, column=2, padx=20)

    # ── Koneksi WiFi TCP ──────────────────────────────────────
    def toggle_connect(self):
        if self.sock:
            self._disconnect()
        else:
            threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self):
        self.update_ui("⏳ Menghubungkan ke ESP32...")
        self.root.after(0, lambda: self.btn_connect.config(state="disabled"))
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ESP32_IP, ESP32_PORT))
            s.settimeout(None)
            self.sock = s
            self.update_ui("✅ Terhubung ke ESP32!")
            self.status_label.config(fg="#4ade80")
            self.root.after(0, lambda: (
                self.btn_connect.config(text="🔌  DISCONNECT",
                                        state="normal", bg="#ef4444"),
                self.btn_start.config(state="normal")
            ))
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            self.update_ui(f"❌ Gagal konek: {e}  |  Pastikan WiFi laptop sudah ke ESP32_SAMPAH")
            self.status_label.config(fg="#ef4444")
            self.root.after(0, lambda: self.btn_connect.config(state="normal"))
            self.sock = None

    def _disconnect(self):
        global running
        running = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        self.update_ui("🔌 Terputus dari ESP32.")
        self.status_label.config(fg="#94a3b8")
        self.root.after(0, lambda: (
            self.btn_connect.config(text="🔗  CONNECT KE ESP32",
                                    state="normal", bg="#38bdf8"),
            self.btn_start.config(state="disabled"),
            self.btn_stop.config(state="disabled")
        ))

    # ── Update UI ─────────────────────────────────────────────
    def update_ui(self, status=None, result=None):
        def _do():
            if status is not None:
                self.status_text.set(status)
            if result is not None:
                self.detect_text.set(result)
                if result == "ORGANIK":
                    self.result_box.config(bg="#22c55e")
                elif result == "ANORGANIK":
                    self.result_box.config(bg="#ef4444")
                else:
                    self.result_box.config(bg="#1e293b")
        self.root.after(0, _do)

    # ── Start / Stop ──────────────────────────────────────────
    def start(self):
        global running
        if not self.sock:
            self.update_ui("⚠ Hubungkan ke ESP32 terlebih dahulu!")
            return
        running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        threading.Thread(target=self.run_voice, daemon=True).start()

    def stop(self):
        global running
        running = False
        self.update_ui("STOPPED", "-")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def exit_app(self):
        global running
        running = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.root.destroy()

    # ── Voice Loop ────────────────────────────────────────────
    def run_voice(self):
        recognizer = sr.Recognizer()

        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)

                while running:
                    try:
                        self.update_ui("LISTENING...", None)

                        audio = recognizer.listen(source, timeout=5)
                        text  = recognizer.recognize_google(audio, language="id-ID")

                        result = classify_text(text)
                        self.update_ui("DETECTED", result)

                        if result == "ORGANIK":
                            send_command(self.sock, result)          # kirim dulu
                            play_feedback_mp3(ORGANIK_AUDIO)         # baru audio

                        elif result == "ANORGANIK":
                            send_command(self.sock, result)
                            play_feedback_mp3(UNORGANIK_AUDIO)

                        elif result == "TUTUP":
                            send_command(self.sock, result)
                            play_feedback_mp3(TUTUP_AUDIO)

                        time.sleep(1)

                    except sr.WaitTimeoutError:
                        self.update_ui("LISTENING...", None)
                    except sr.UnknownValueError:
                        self.update_ui("SUARA TIDAK JELAS", "-")
                    except sr.RequestError as e:
                        self.update_ui(f"ERROR API: {e}", "-")
                    except Exception as e:
                        self.update_ui(f"ERROR: {e}", "-")

        except Exception as e:
            self.update_ui(f"ERROR MIKROFON: {e}", "-")

        finally:
            self.root.after(0, lambda: (
                self.btn_start.config(state="normal"),
                self.btn_stop.config(state="disabled")
            ))

# ================= MAIN =================
if __name__ == "__main__":
    root = tk.Tk()
    app  = App(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    root.mainloop()
