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

}

void loop() {

  if (SerialBT.available()) {

    String cmd = SerialBT.readStringUntil('\n');
    cmd.trim();

    if (cmd == "organik") {

      servoOrganik.write(90);
      delay(3000);
      servoOrganik.write(0);

    }

    if (cmd == "anorganik") {

      servoAnorganik.write(90);
      delay(3000);
      servoAnorganik.write(0);

    }

  }

}
