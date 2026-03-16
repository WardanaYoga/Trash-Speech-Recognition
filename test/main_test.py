import speech_recognition as sr
import serial
import pyttsx3

# koneksi ESP32 bluetooth
esp32 = serial.Serial("COM6", 9600)

# text to speech
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

recognizer = sr.Recognizer()

while True:

    with sr.Microphone() as source:
        print("Silakan bicara...")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio, language="id-ID")
        text = text.lower()

        print("Terdeteksi:", text)

        if "organik" in text:

            esp32.write(b'organik\n')
            speak("Sampah organik dibuka")

        elif "anorganik" in text:

            esp32.write(b'anorganik\n')
            speak("Sampah anorganik dibuka")

        elif "tutup" in text:

            esp32.write(b'tutup\n')
            speak("Tempat sampah ditutup")

    except:
        print("Suara tidak dikenali")
