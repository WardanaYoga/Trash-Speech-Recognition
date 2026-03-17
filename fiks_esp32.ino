#include <BluetoothSerial.h>
#include <ESP32Servo.h>

BluetoothSerial SerialBT;

Servo servoOrganik;
Servo servoAnorganik;

void setup() {

  Serial.begin(115200);
  SerialBT.begin("ESP32_SAMPAH");

  servoOrganik.attach(18);
  servoAnorganik.attach(19);

  // === POSISI DEFAULT ===
  servoOrganik.write(0);
  servoAnorganik.write(0);

  delay(500); // kasih waktu servo untuk mencapai posisi awal
}

void loop() {

  if (SerialBT.available()) {

    char cmd = SerialBT.read();  // baca 1 karakter

    if (cmd == '0') {  // organik
      servoOrganik.write(90);
      delay(3000);
      servoOrganik.write(0);
    }

    else if (cmd == '1') {  // anorganik
      servoAnorganik.write(90);
      delay(3000);
      servoAnorganik.write(0);
    }

    else if (cmd == '2'){
      servoOrganik.write(0);
      servoAnorganik.write(0);
    }

  }

}
