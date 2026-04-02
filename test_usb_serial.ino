#include <ESP32Servo.h>

Servo servo1;

void setup() {
  Serial.begin(115200);

  servo1.attach(19);
  servo1.write(90);

  Serial.println("ESP32 READY");
}

void loop() {

  if (Serial.available()) {

    char cmd = Serial.read();

    Serial.print("Diterima: ");
    Serial.println(cmd);

    if (cmd == '0') {  // ORGANIK
      Serial.println("Gerak ke 0");
      servo1.write(0);
      delay(5000);
      servo1.write(90);
      Serial.println("Kembali ke 90");
    }

    else if (cmd == '1') {  // ANORGANIK
      Serial.println("Gerak ke 180");
      servo1.write(180);
      delay(5000);
      servo1.write(90);
      Serial.println("Kembali ke 90");
    }

    else if (cmd == '2') {  // TUTUP
      Serial.println("Reset ke 90");
      servo1.write(90);
    }
  }
}
