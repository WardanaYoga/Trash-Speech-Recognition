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

  Serial.println("ESP32 siap");

}

void loop() {

  if (SerialBT.available()) {

    String cmd = SerialBT.readStringUntil('\n');
    cmd.trim();

    Serial.print("Perintah diterima: ");
    Serial.println(cmd);

    if (cmd == "organik") {

      servoOrganik.write(90);
      delay(3000);
      servoOrganik.write(0);

      SerialBT.println("ORGANIK_BERHASIL");

    }

    else if (cmd == "anorganik") {

      servoAnorganik.write(90);
      delay(3000);
      servoAnorganik.write(0);

      SerialBT.println("ANORGANIK_BERHASIL");

    }

    else if (cmd == "tutup") {

      servoOrganik.write(0);
      servoAnorganik.write(0);

      SerialBT.println("TUTUP_BERHASIL");

    }

  }

}
