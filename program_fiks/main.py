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

        # FULLSCREEN
        self.attributes("-fullscreen", True)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Dynamic font scaling
        title_size = int(screen_width * 0.03)
        subtitle_size = int(screen_width * 0.015)
        status_size = int(screen_width * 0.018)
        result_size = int(screen_width * 0.05)
        button_size = int(screen_width * 0.015)

        self.running = False

        # HEADER
        self.header = ctk.CTkLabel(self, text="SMART TRASH BIN",
                                   font=("Segoe UI", title_size, "bold"))
        self.header.pack(pady=20)

        self.sub = ctk.CTkLabel(self, text="TEKNIK MESIN UNIVERSITAS BRAWIJAYA",
                                font=("Segoe UI", subtitle_size))
        self.sub.pack()

        # STATUS
        self.status = ctk.CTkLabel(self, text="● DISCONNECTED",
                                   text_color="red",
                                   font=("Segoe UI", status_size, "bold"))
        self.status.pack(pady=20)

        # RESULT
        self.result_box = ctk.CTkLabel(self, text="READY",
                                       width=int(screen_width * 0.5),
                                       height=int(screen_height * 0.2),
                                       corner_radius=30,
                                       font=("Segoe UI", result_size, "bold"))
        self.result_box.pack(pady=30)

        # CONTROL
        control = ctk.CTkFrame(self)
        control.pack(pady=20)

        self.start_btn = ctk.CTkButton(control, text="START",
                                       command=self.start,
                                       width=200,
                                       height=60,
                                       font=("Segoe UI", button_size, "bold"))
        self.start_btn.grid(row=0, column=0, padx=20)

        self.stop_btn = ctk.CTkButton(control, text="STOP",
                                      command=self.stop,
                                      fg_color="red",
                                      width=200,
                                      height=60,
                                      font=("Segoe UI", button_size, "bold"))
        self.stop_btn.grid(row=0, column=1, padx=20)

        # LOG
        self.log = ctk.CTkTextbox(self, height=int(screen_height * 0.25))
        self.log.pack(padx=40, pady=20, fill="both", expand=True)

        # EXIT BUTTON (hidden corner)
        self.bind("<Escape>", lambda e: self.destroy())

        # THREAD
        threading.Thread(target=self.connection_monitor, daemon=True).start()

    def log_print(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def update_status(self, connected):
        if connected:
            self.status.configure(text="● CONNECTED", text_color="green")
        else:
            self.status.configure(text="● DISCONNECTED", text_color="red")

    def connection_monitor(self):
        while True:
            status = check_connection()
            self.update_status(status)
            time.sleep(PING_INTERVAL)

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_loop, daemon=True).start()
            self.log_print("System started")

    def stop(self):
        self.running = False
        self.log_print("System stopped")

    def run_loop(self):
        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)

            while self.running:
                try:
                    self.result_box.configure(text="LISTENING...")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)

                    self.result_box.configure(text="PROCESSING...")
                    text = recognizer.recognize_google(audio, language="id-ID")
                    result = classify_text(text)

                    self.result_box.configure(text=result)
                    self.log_print(f"Voice: {text}")

                    if result == "ORGANIK":
                        send_command(result)
                        play_audio(ORGANIK_AUDIO)

                    elif result == "ANORGANIK":
                        send_command(result)
                        play_audio(ANORGANIK_AUDIO)

                except Exception as e:
                    self.log_print(f"Error: {e}")

# ================= MAIN =================
if __name__ == "__main__":
    app = App()
    app.mainloop()
