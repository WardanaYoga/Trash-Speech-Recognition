import customtkinter as ctk
import threading
import re
from pathlib import Path
from ctypes import windll
import requests
import speech_recognition as sr
import time

# ================= CONFIG =================
ESP32_URL = "http://esp32.local"
REQUEST_TIMEOUT_SECONDS = 1.5
PING_INTERVAL = 3

BASE_DIR = Path(__file__).resolve().parent
ORGANIK_AUDIO = BASE_DIR / "Organik.mp3"
ANORGANIK_AUDIO = BASE_DIR / "Unorganik.mp3"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ================= CORE =================
def classify_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("non-organik", "non organik")
    text = text.replace("an organik", "anorganik")
    text = text.replace("un organik", "unorganik")

    if re.search(r"\b(anorganik|unorganik|non organik)\b", text):
        return "ANORGANIK"
    if re.search(r"\borganik\b", text):
        return "ORGANIK"
    return "TIDAK DIKENALI"


def _mci_send(command: str):
    windll.winmm.mciSendStringW(command, None, 0, None)


def play_audio(path: Path):
    if not path.exists():
        return
    alias = "audio"
    _mci_send(f"close {alias}")
    _mci_send(f'open "{str(path)}" type mpegvideo alias {alias}')
    _mci_send(f"play {alias}")


def send_command(result: str):
    try:
        if result == "ORGANIK":
            requests.get(f"{ESP32_URL}/organik", timeout=REQUEST_TIMEOUT_SECONDS)
        elif result == "ANORGANIK":
            requests.get(f"{ESP32_URL}/anorganik", timeout=REQUEST_TIMEOUT_SECONDS)
    except:
        pass


def check_connection():
    try:
        requests.get(ESP32_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        return True
    except:
        return False

# ================= GUI =================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── FULLSCREEN ──────────────────────────────────────────────────
        self.attributes("-fullscreen", True)
        self.update_idletasks()

        W = self.winfo_screenwidth()
        H = self.winfo_screenheight()

        # ── FONT SIZES (relative to screen) ────────────────────────────
        FS = lambda pct: int(W * pct)
        title_size    = FS(0.030)
        subtitle_size = FS(0.014)
        status_size   = FS(0.016)
        result_size   = FS(0.060)
        label_size    = FS(0.013)
        button_size   = FS(0.014)
        log_size      = FS(0.011)

        self.running = False

        # ── ROOT GRID: 1 column, rows with weight ──────────────────────
        self.grid_rowconfigure(0, weight=0)   # header
        self.grid_rowconfigure(1, weight=0)   # subtitle
        self.grid_rowconfigure(2, weight=0)   # status
        self.grid_rowconfigure(3, weight=2)   # result box  ← grows more
        self.grid_rowconfigure(4, weight=0)   # buttons
        self.grid_rowconfigure(5, weight=0)   # voice label
        self.grid_rowconfigure(6, weight=1)   # log         ← grows less
        self.grid_columnconfigure(0, weight=1)

        PAD_X = int(W * 0.04)

        # ── HEADER ─────────────────────────────────────────────────────
        self.header = ctk.CTkLabel(
            self, text="🗑  SMART TRASH BIN",
            font=("Segoe UI", title_size, "bold"))
        self.header.grid(row=0, column=0, pady=(int(H*0.03), 4), sticky="ew")

        self.sub = ctk.CTkLabel(
            self, text="Teknik Mesin — Universitas Brawijaya",
            font=("Segoe UI", subtitle_size))
        self.sub.grid(row=1, column=0, pady=(0, int(H*0.02)), sticky="ew")

        # ── CONNECTION STATUS ───────────────────────────────────────────
        self.status = ctk.CTkLabel(
            self, text="● DISCONNECTED",
            text_color="red",
            font=("Segoe UI", status_size, "bold"))
        self.status.grid(row=2, column=0, pady=(0, int(H*0.015)), sticky="ew")

        # ── RESULT BOX ─────────────────────────────────────────────────
        self.result_box = ctk.CTkLabel(
            self, text="READY",
            corner_radius=30,
            font=("Segoe UI", result_size, "bold"))
        self.result_box.grid(
            row=3, column=0,
            padx=PAD_X, pady=int(H*0.015),
            sticky="nsew")

        # ── CONTROL BUTTONS ────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=int(H*0.015))

        btn_w = int(W * 0.14)
        btn_h = int(H * 0.07)

        self.start_btn = ctk.CTkButton(
            btn_frame, text="▶  START",
            command=self.start,
            width=btn_w, height=btn_h,
            font=("Segoe UI", button_size, "bold"))
        self.start_btn.grid(row=0, column=0, padx=int(W*0.02))

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="■  STOP",
            command=self.stop,
            fg_color="#c0392b", hover_color="#922b21",
            width=btn_w, height=btn_h,
            font=("Segoe UI", button_size, "bold"))
        self.stop_btn.grid(row=0, column=1, padx=int(W*0.02))

        # ── VOICE LOG LABEL ────────────────────────────────────────────
        self.voice_label = ctk.CTkLabel(
            self, text="LOG SUARA",
            font=("Segoe UI", label_size, "bold"),
            anchor="w")
        self.voice_label.grid(
            row=5, column=0,
            padx=PAD_X, pady=(int(H*0.01), 2),
            sticky="w")

        # ── LOG BOX ────────────────────────────────────────────────────
        self.log = ctk.CTkTextbox(
            self,
            font=("Consolas", log_size),
            corner_radius=12)
        self.log.grid(
            row=6, column=0,
            padx=PAD_X, pady=(0, int(H*0.025)),
            sticky="nsew")

        # ── KEYBOARD EXIT ──────────────────────────────────────────────
        self.bind("<Escape>", lambda e: self.destroy())

        # ── BACKGROUND MONITOR ─────────────────────────────────────────
        threading.Thread(target=self.connection_monitor, daemon=True).start()

    # ── HELPERS ────────────────────────────────────────────────────────
    def log_print(self, text):
        ts = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {text}\n")
        self.log.see("end")

    def update_status(self, connected):
        if connected:
            self.status.configure(text="● CONNECTED", text_color="#2ecc71")
        else:
            self.status.configure(text="● DISCONNECTED", text_color="#e74c3c")

    def connection_monitor(self):
        while True:
            ok = check_connection()
            self.after(0, self.update_status, ok)
            time.sleep(PING_INTERVAL)

    # ── START / STOP ───────────────────────────────────────────────────
    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_loop, daemon=True).start()
            self.log_print("System started")

    def stop(self):
        self.running = False
        self.after(0, self.result_box.configure, {"text": "READY"})
        self.log_print("System stopped")

    # ── RECOGNITION LOOP ───────────────────────────────────────────────
    def run_loop(self):
        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)

            while self.running:
                try:
                    self.after(0, self.result_box.configure, {"text": "🎤  LISTENING..."})
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)

                    self.after(0, self.result_box.configure, {"text": "⏳  PROCESSING..."})
                    text = recognizer.recognize_google(audio, language="id-ID")
                    result = classify_text(text)

                    self.after(0, self.result_box.configure, {"text": result})
                    self.after(0, self.log_print, f"Suara  : {text}")
                    self.after(0, self.log_print, f"Hasil  : {result}")

                    if result == "ORGANIK":
                        threading.Thread(target=send_command, args=(result,), daemon=True).start()
                        play_audio(ORGANIK_AUDIO)

                    elif result == "ANORGANIK":
                        threading.Thread(target=send_command, args=(result,), daemon=True).start()
                        play_audio(ANORGANIK_AUDIO)

                except sr.WaitTimeoutError:
                    pass  # silent timeout — just loop again
                except Exception as e:
                    self.after(0, self.log_print, f"Error  : {e}")

# ================= MAIN =================
if __name__ == "__main__":
    app = App()
    app.mainloop()
