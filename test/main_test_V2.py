import speech_recognition as sr
import serial
import pyttsx3

esp32 = serial.Serial("COM6", 9600, timeout=1)

engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

recognizer = sr.Recognizer()

while True:

    # ========================
    # 1. DENGAR SUARA
    # ========================
    with sr.Microphone() as source:

        print("Silakan bicara...")
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

    # ========================
    # 2. CEK FEEDBACK ESP32
    # ========================
    if esp32.in_waiting > 0:

        response = esp32.readline().decode().strip()
        print("ESP32:", response)

        if response == "ORGANIK_BERHASIL":
            speak("Sampah organik berhasil dibuka")

        elif response == "ANORGANIK_BERHASIL":
            speak("Sampah anorganik berhasil dibuka")

        elif response == "TUTUP_BERHASIL":
            speak("Tempat sampah ditutup")
