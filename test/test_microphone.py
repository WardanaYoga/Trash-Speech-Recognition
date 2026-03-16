import speech_recognition as sr

recognizer = sr.Recognizer()

with sr.Microphone() as source:
    print("Silakan bicara...")
    
    recognizer.adjust_for_ambient_noise(source)
    
    audio = recognizer.listen(source)

try:
    text = recognizer.recognize_google(audio, language="id-ID")
    print("Teks terdeteksi:", text)

except sr.UnknownValueError:
    print("Suara tidak dikenali")

except sr.RequestError:
    print("Tidak bisa terhubung ke layanan speech recognition")
