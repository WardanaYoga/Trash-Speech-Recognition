#include <BluetoothSerial.h>
#include <ESP32Servo.h>

BluetoothSerial SerialBT;

Servo servo1;

void setup() {

  Serial.begin(115200);
  SerialBT.begin("ESP32_SAMPAH");

  servo1.attach(19);

  // === POSISI DEFAULT ===
  servo1.write(90);

  delay(500); // kasih waktu servo untuk mencapai posisi awal
}

void loop() {

  if (SerialBT.available()) {

    char cmd = SerialBT.read();  // baca 1 karakter

    if (cmd == '0') {  // organik
      servo1.write(0);
      delay(3000);
      servo1.write(90);
    }

    else if (cmd == '1') {  // anorganik
      servo1.write(180);
      delay(3000);
      servo1.write(90);
    }

    else if (cmd == '2'){
      servo1.write(90);
      servo1.write(90);
    }

  }

}
