"""
Voice Recognition + Bluetooth ESP32 (Organik/Anorganik)

Fungsi:
- Dengarkan suara "organik" atau "unorganik/anorganik"
- Putar feedback audio MP3 lokal
- Kirim perintah Bluetooth ke ESP32:
  - '0' untuk organik
  - '1' untuk anorganik

Sesuai sketch ESP32:
if cmd == '0' => servo organik
if cmd == '1' => servo anorganik
"""

from pathlib import Path
from ctypes import windll, create_unicode_buffer
import re
import time

import speech_recognition as sr

try:
    import serial
    from serial.tools import list_ports
except ImportError as exc:
    raise SystemExit(
        "Modul pyserial belum terpasang. Install dulu: pip install pyserial"
    ) from exc


BASE_DIR = Path(__file__).resolve().parent
ORGANIK_AUDIO = BASE_DIR / "Organik.mp3"
UNORGANIK_AUDIO = BASE_DIR / "Unorganik.mp3"

SERIAL_BAUDRATE = 115200
POST_FEEDBACK_PAUSE_SECONDS = 1.2
POST_SEND_COOLDOWN_SECONDS = 1.0


def classify_text(text: str) -> str:
    """Klasifikasi teks menjadi ORGANIK, ANORGANIK, atau TIDAK DIKENALI."""
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
    """Play MP3 sinkron dengan MCI agar aplikasi menunggu sampai audio selesai."""
    if not mp3_path.exists():
        print(f"[WARN] File audio tidak ditemukan: {mp3_path.name}")
        return

    alias = "vr_feedback"
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


def choose_serial_port() -> str:
    """Tampilkan COM yang tersedia, lalu user memilih satu port."""
    ports = list(list_ports.comports())

    if not ports:
        raise RuntimeError("Tidak ada COM port terdeteksi. Pastikan Bluetooth ESP32 sudah paired.")

    print("\nCOM port terdeteksi:")
    for idx, port in enumerate(ports, start=1):
        print(f"  {idx}. {port.device} - {port.description}")

    while True:
        choice = input("Pilih nomor COM port: ").strip()
        if not choice.isdigit():
            print("Input harus angka.")
            continue

        selected_idx = int(choice)
        if 1 <= selected_idx <= len(ports):
            return ports[selected_idx - 1].device

        print(f"Pilih angka antara 1 sampai {len(ports)}.")


def send_command(ser: serial.Serial, result: str):
    """Kirim karakter perintah sesuai sketch ESP32."""
    if result == "ORGANIK":
        ser.write(b"0")
        print("[BT] Kirim -> '0' (ORGANIK)")
    elif result == "ANORGANIK":
        ser.write(b"1")
        print("[BT] Kirim -> '1' (ANORGANIK)")


def run_loop():
    recognizer = sr.Recognizer()

    print("=" * 65)
    print("VOICE RECOGNITION + BLUETOOTH ESP32")
    print("Perintah: '0' = Organik, '1' = Anorganik")
    print("Tekan Ctrl+C untuk berhenti")
    print("=" * 65)
    print(f"Audio ORGANIK   : {ORGANIK_AUDIO.name}")
    print(f"Audio ANORGANIK : {UNORGANIK_AUDIO.name}")

    try:
        port = choose_serial_port()
        print(f"\nMembuka koneksi Bluetooth COM: {port} @ {SERIAL_BAUDRATE}")

        with serial.Serial(port, SERIAL_BAUDRATE, timeout=1) as ser:
            time.sleep(2)
            print("Koneksi Bluetooth siap.")

            with sr.Microphone() as source:
                print("\nKalibrasi noise ruangan...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Siap mendengarkan. Ucapkan 'organik' atau 'unorganik'.\n")

                while True:
                    try:
                        print("Dengarkan...")
                        audio = recognizer.listen(source, timeout=10, phrase_time_limit=4)
                        spoken_text = recognizer.recognize_google(audio, language="id-ID").lower()

                        result = classify_text(spoken_text)
                        print(f"Terdeteksi: {spoken_text}")
                        print(f"Hasil     : {result}")

                        if result == "ORGANIK":
                            play_feedback_mp3(ORGANIK_AUDIO)
                            time.sleep(POST_FEEDBACK_PAUSE_SECONDS)
                            send_command(ser, result)
                            time.sleep(POST_SEND_COOLDOWN_SECONDS)
                        elif result == "ANORGANIK":
                            play_feedback_mp3(UNORGANIK_AUDIO)
                            time.sleep(POST_FEEDBACK_PAUSE_SECONDS)
                            send_command(ser, result)
                            time.sleep(POST_SEND_COOLDOWN_SECONDS)
                        else:
                            print("Tidak ada perintah Bluetooth yang dikirim.")

                        print()

                    except sr.WaitTimeoutError:
                        print("Tidak ada suara. Coba lagi.\n")
                    except sr.UnknownValueError:
                        print("Suara kurang jelas. Coba ulangi.\n")
                    except sr.RequestError as err:
                        print(f"Error layanan speech recognition: {err}")
                        break

    except KeyboardInterrupt:
        print("\nProgram dihentikan pengguna.")
    except Exception as err:
        print(f"Error: {err}")


if __name__ == "__main__":
    run_loop()
