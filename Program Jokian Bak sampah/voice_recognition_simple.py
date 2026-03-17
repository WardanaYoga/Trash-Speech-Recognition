"""
Program Sederhana Pengenalan Suara Organik/Anorganik
Versi Looping - terus mendengarkan sampai user menghentikan
"""

import speech_recognition as sr
import re
import time
from pathlib import Path
from ctypes import windll, create_unicode_buffer

def classify_text(text):
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


BASE_DIR = Path(__file__).resolve().parent
ORGANIK_AUDIO = BASE_DIR / "Organik.mp3"
UNORGANIK_AUDIO = BASE_DIR / "Unorganik.mp3"


def _mci_send(command):
    result = windll.winmm.mciSendStringW(command, None, 0, None)
    if result != 0:
        error_buffer = create_unicode_buffer(255)
        windll.winmm.mciGetErrorStringW(result, error_buffer, len(error_buffer))
        return error_buffer.value or f"MCI error code: {result}"
    return None


def play_feedback_mp3(mp3_path):
    """Play MP3 secara sinkron agar program menunggu sampai audio selesai."""
    if not mp3_path.exists():
        print(f"⚠️ File audio tidak ditemukan: {mp3_path.name}")
        return

    alias = "vr_feedback"
    safe_path = str(mp3_path).replace('"', '')

    # Tutup alias lama jika masih aktif, abaikan error bila tidak ada.
    _mci_send(f"close {alias}")

    open_err = _mci_send(f'open "{safe_path}" type mpegvideo alias {alias}')
    if open_err:
        print(f"⚠️ Gagal membuka audio {mp3_path.name}: {open_err}")
        return

    play_err = _mci_send(f"play {alias} wait")
    if play_err:
        print(f"⚠️ Gagal memutar audio {mp3_path.name}: {play_err}")

    _mci_send(f"close {alias}")


def recognize_simple_loop():
    """Versi simple yang looping sampai user menghentikan program."""
    recognizer = sr.Recognizer()

    print("=" * 55)
    print("PROGRAM SIMPLE LOOPING: ORGANIK vs UNORGANIK/ANORGANIK")
    print("Tekan Ctrl+C untuk berhenti")
    print("=" * 55)
    print(f"🔊 Audio ORGANIK: {ORGANIK_AUDIO.name}")
    print(f"🔊 Audio UNORGANIK: {UNORGANIK_AUDIO.name}")

    try:
        with sr.Microphone() as source:
            print("\n🔧 Kalibrasi noise ruangan...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Siap mendengarkan. Silakan bicara.\n")

            while True:
                try:
                    print("🎤 Ucapkan: 'organik' atau 'unorganik'...")
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=4)
                    text = recognizer.recognize_google(audio, language='id-ID').lower()

                    result = classify_text(text)
                    print(f"📝 Terdeteksi: {text}")
                    print(f"✅ HASIL: {result}\n")

                    if result == "ORGANIK":
                        play_feedback_mp3(ORGANIK_AUDIO)
                        print("⏸️ Pause 1.5 detik agar audio feedback tidak terdeteksi ulang...\n")
                        time.sleep(1)
                    elif result == "ANORGANIK":
                        play_feedback_mp3(UNORGANIK_AUDIO)
                        print("⏸️ Pause 1.5 detik agar audio feedback tidak terdeteksi ulang...\n")
                        time.sleep(1)

                except sr.WaitTimeoutError:
                    print("⏰ Tidak ada suara. Coba lagi...\n")
                except sr.UnknownValueError:
                    print("❌ Suara kurang jelas. Coba ulangi...\n")
                except sr.RequestError as e:
                    print(f"❌ Error layanan speech recognition: {e}")
                    break

    except KeyboardInterrupt:
        print("\n👋 Program dihentikan pengguna.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    recognize_simple_loop()
