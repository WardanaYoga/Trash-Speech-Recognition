import re
import threading
from pathlib import Path
from ctypes import windll, create_unicode_buffer

import requests
import speech_recognition as sr

ESP32_URL = "http://esp32.local"
# fallback contoh:
# ESP32_URL = "http://192.168.1.50"

BASE_DIR = Path(__file__).resolve().parent
ORGANIK_AUDIO = BASE_DIR / "Organik.mp3"
ANORGANIK_AUDIO = BASE_DIR / "Unorganik.mp3"

REQUEST_TIMEOUT_SECONDS = 1.5


def classify_text(text: str) -> str:
    normalized_text = text.lower().strip()
    normalized_text = normalized_text.replace("non-organik", "non organik")
    normalized_text = normalized_text.replace("an organik", "anorganik")
    normalized_text = normalized_text.replace("un organik", "unorganik")

    if re.search(r"\b(anorganik|unorganik|non organik)\b", normalized_text):
        return "ANORGANIK"
    if re.search(r"\borganik\b", normalized_text):
        return "ORGANIK"
    return "TIDAK DIKENALI"


def _mci_send(command: str):
    result = windll.winmm.mciSendStringW(command, None, 0, None)
    if result != 0:
        error_buffer = create_unicode_buffer(255)
        windll.winmm.mciGetErrorStringW(result, error_buffer, len(error_buffer))
        return error_buffer.value or f"MCI error code: {result}"
    return None


def play_feedback_mp3(mp3_path: Path):
    if not mp3_path.exists():
        print(f"[WARN] File audio tidak ditemukan: {mp3_path.name}")
        return

    alias = f"vr_feedback_{threading.get_ident()}"
    safe_path = str(mp3_path).replace('"', "")

    _mci_send(f"close {alias}")

    open_err = _mci_send(f'open "{safe_path}" type mpegvideo alias {alias}')
    if open_err:
        print(f"[WARN] Gagal membuka audio {mp3_path.name}: {open_err}")
        return

    play_err = _mci_send(f"play {alias} wait")
    if play_err:
        print(f"[WARN] Gagal memutar audio {mp3_path.name}: {play_err}")

    _mci_send(f"close {alias}")


def play_audio_async(mp3_path: Path):
    thread = threading.Thread(target=play_feedback_mp3, args=(mp3_path,), daemon=True)
    thread.start()


def send_command(result: str):
    try:
        if result == "ORGANIK":
            response = requests.get(f"{ESP32_URL}/organik", timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            print("[WiFi] Kirim -> ORGANIK")

        elif result == "ANORGANIK":
            response = requests.get(f"{ESP32_URL}/anorganik", timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            print("[WiFi] Kirim -> ANORGANIK")

    except requests.RequestException as exc:
        print(f"[ERROR] Gagal kirim ke ESP32: {exc}")


def test_esp32_connection():
    try:
        response = requests.get(f"{ESP32_URL}/", timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        print(f"[OK] ESP32 reachable -> {ESP32_URL}")
        return True
    except requests.RequestException as exc:
        print(f"[ERROR] ESP32 tidak bisa diakses di {ESP32_URL}: {exc}")
        return False


def run_loop():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.non_speaking_duration = 0.5

    print("=" * 60)
    print("VOICE RECOGNITION + WIFI ESP32")
    print("Perintah: 'organik' / 'anorganik'")
    print("Tekan Ctrl+C untuk berhenti")
    print("=" * 60)
    print(f"ESP32 URL        : {ESP32_URL}")
    print(f"Audio ORGANIK    : {ORGANIK_AUDIO.name}")
    print(f"Audio ANORGANIK  : {ANORGANIK_AUDIO.name}")

    if not test_esp32_connection():
        return

    try:
        with sr.Microphone() as source:
            print("\nKalibrasi noise ruangan...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Siap mendengarkan. Ucapkan 'organik' atau 'anorganik'.\n")

            while True:
                try:
                    print("Listening...")
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=4)

                    spoken_text = recognizer.recognize_google(audio, language="id-ID").lower()
                    result = classify_text(spoken_text)

                    print(f"Terdeteksi: {spoken_text}")
                    print(f"Hasil     : {result}")

                    if result == "ORGANIK":
                        send_command(result)
                        play_audio_async(ORGANIK_AUDIO)

                    elif result == "ANORGANIK":
                        send_command(result)
                        play_audio_async(ANORGANIK_AUDIO)

                    else:
                        print("Tidak ada perintah yang dikirim.")

                    print()

                except sr.WaitTimeoutError:
                    print("Tidak ada suara. Coba lagi.\n")

                except sr.UnknownValueError:
                    print("Suara kurang jelas. Coba ulangi.\n")

                except sr.RequestError as err:
                    print(f"Error layanan speech recognition: {err}\n")

    except KeyboardInterrupt:
        print("\nProgram dihentikan pengguna.")

    except Exception as err:
        print(f"Error: {err}")


if __name__ == "__main__":
    run_loop()
