#include <BluetoothSerial.h>
#include <ESP32Servo.h>

BluetoothSerial SerialBT;
Servo servo1;

void setup() {
  Serial.begin(115200);
  SerialBT.begin("ESP32_SAMPAH");
  servo1.attach(19);

  // Posisi default (tutup / netral)
  servo1.write(90);
  delay(500);

  Serial.println("ESP32 siap. Menunggu perintah...");
}

void loop() {
  if (SerialBT.available()) {
    char cmd = SerialBT.read();

    Serial.print("Perintah diterima: ");
    Serial.println(cmd);

    if (cmd == '0') {        // ORGANIK → kiri
      servo1.write(0);
      delay(3000);
      servo1.write(90);

    } else if (cmd == '1') { // ANORGANIK → kanan
      servo1.write(180);
      delay(3000);
      servo1.write(90);

    } else if (cmd == '2') { // TUTUP → netral
      servo1.write(90);      // ✅ Cukup satu kali
    }

    // ✅ Bersihkan sisa buffer agar perintah lama tidak menumpuk
    while (SerialBT.available()) {
      SerialBT.read();
    }

    delay(200); // debounce kecil
  }
}
