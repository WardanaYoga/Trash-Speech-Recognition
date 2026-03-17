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

# ================= CONFIG =================
BASE_DIR = Path(__file__).resolve().parent
ORGANIK_AUDIO = BASE_DIR / "Organik.mp3"
UNORGANIK_AUDIO = BASE_DIR / "Unorganik.mp3"
TUTUP_AUDIO = BASE_DIR / "Tutup.mp3"

SERIAL_BAUDRATE = 115200
running = False

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

def get_ports():
    return [port.device for port in list_ports.comports()]

def send_command(ser, result):
    if result == "ORGANIK":
        ser.write(b"0")
    elif result == "ANORGANIK":
        ser.write(b"1")
    elif result == "TUTUP":
        ser.write(b"2")

# ================= GUI =================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Waste System")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#0f172a")

        self.selected_port = tk.StringVar()
        self.status_text = tk.StringVar(value="READY")
        self.detect_text = tk.StringVar(value="-")

        # TITLE
        tk.Label(root, text="SMART WASTE SYSTEM",
                 font=("Segoe UI", 40, "bold"),
                 fg="white", bg="#0f172a").pack(pady=30)

        # === COM SELECT ===
        com_frame = tk.Frame(root, bg="#0f172a")
        com_frame.pack(pady=10)

        tk.Label(com_frame, text="PILIH COM:",
                 font=("Segoe UI", 14),
                 fg="white", bg="#0f172a").grid(row=0, column=0, padx=10)

        self.com_box = ttk.Combobox(com_frame,
                                   textvariable=self.selected_port,
                                   font=("Segoe UI", 12),
                                   width=15,
                                   state="readonly")
        self.com_box.grid(row=0, column=1, padx=10)

        tk.Button(com_frame, text="REFRESH",
                  command=self.refresh_ports,
                  bg="#38bdf8", fg="white").grid(row=0, column=2, padx=10)

        # STATUS
        tk.Label(root, textvariable=self.status_text,
                 font=("Segoe UI", 20),
                 fg="#38bdf8", bg="#0f172a").pack(pady=10)

        # RESULT BOX
        self.result_box = tk.Label(root,
                                  textvariable=self.detect_text,
                                  font=("Segoe UI", 50, "bold"),
                                  width=20, height=2,
                                  bg="#1e293b", fg="white")
        self.result_box.pack(pady=40)

        # BUTTONS
        frame = tk.Frame(root, bg="#0f172a")
        frame.pack(pady=20)

        tk.Button(frame, text="START",
                  font=("Segoe UI", 16, "bold"),
                  bg="#22c55e", fg="white",
                  width=10, command=self.start).grid(row=0, column=0, padx=20)

        tk.Button(frame, text="STOP",
                  font=("Segoe UI", 16, "bold"),
                  bg="#f59e0b", fg="white",
                  width=10, command=self.stop).grid(row=0, column=1, padx=20)

        tk.Button(frame, text="EXIT",
                  font=("Segoe UI", 16, "bold"),
                  bg="#ef4444", fg="white",
                  width=10, command=self.exit_app).grid(row=0, column=2, padx=20)

        self.refresh_ports()

    def refresh_ports(self):
        ports = get_ports()
        self.com_box['values'] = ports
        if ports:
            self.com_box.current(0)

    def update_ui(self, status=None, result=None):
        if status:
            self.status_text.set(status)

        if result:
            self.detect_text.set(result)

            if result == "ORGANIK":
                self.result_box.config(bg="#22c55e")
            elif result == "ANORGANIK":
                self.result_box.config(bg="#ef4444")
            else:
                self.result_box.config(bg="#1e293b")

    def start(self):
        global running

        if not self.selected_port.get():
            self.update_ui("PILIH COM TERLEBIH DAHULU!", "-")
            return

        running = True
        threading.Thread(target=self.run_voice, daemon=True).start()

    def stop(self):
        global running
        running = False
        self.update_ui("STOPPED", "-")

    def exit_app(self):
        global running
        running = False
        self.root.destroy()

    def run_voice(self):
        recognizer = sr.Recognizer()

        try:
            port = self.selected_port.get()
            ser = serial.Serial(port, SERIAL_BAUDRATE, timeout=1)
            time.sleep(2)

            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)

                while running:
                    try:
                        self.update_ui("LISTENING...", None)

                        audio = recognizer.listen(source, timeout=5)
                        text = recognizer.recognize_google(audio, language="id-ID")

                        result = classify_text(text)
                        self.update_ui("DETECTED", result)

                        if result == "ORGANIK":
                            play_feedback_mp3(ORGANIK_AUDIO)
                            send_command(ser, result)

                        elif result == "ANORGANIK":
                            play_feedback_mp3(UNORGANIK_AUDIO)
                            send_command(ser, result)

                        elif result == "TUTUP":
                            play_feedback_mp3(TUTUP_AUDIO)
                            send_command(ser, result)

                        time.sleep(1)

                    except:
                        self.update_ui("ERROR / NO VOICE", "-")

        except Exception as e:
            self.update_ui(f"ERROR: {e}", "-")

# ================= MAIN =================
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
