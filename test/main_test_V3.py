import speech_recognition as sr
import serial
import pyttsx3
import threading
import time

esp32 = serial.Serial("COM6", 9600, timeout=1)

engine = pyttsx3.init()

def speak_async(text):
    def run():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=run).start()

recognizer = sr.Recognizer()

while True:

    # ======================
    # CEK SERIAL DULU (PENTING)
    # ======================
    while esp32.in_waiting > 0:
        response = esp32.readline().decode().strip()
        print("ESP32:", response)

        if response == "ORGANIK_BERHASIL":
            speak_async("Sampah organik berhasil dibuka")

        elif response == "ANORGANIK_BERHASIL":
            speak_async("Sampah anorganik berhasil dibuka")

        elif response == "TUTUP_BERHASIL":
            speak_async("Tempat sampah ditutup")

    # ======================
    # DENGAR SUARA
    # ======================
    with sr.Microphone() as source:

        print("Silakan bicara...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio, language="id-ID")
        text = text.lower()

        print("Terdeteksi:", text)

        if "organik" in text:
            esp32.write(b'organik\n')

        elif "anorganik" in text:
            esp32.write(b'anorganik\n')

        elif "tutup" in text:
            esp32.write(b'tutup\n')

    except:
        print("Tidak dikenali")

    time.sleep(0.1)
