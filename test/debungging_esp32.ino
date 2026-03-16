#include <BluetoothSerial.h>
#include <ESP32Servo.h>

BluetoothSerial SerialBT;

Servo servoOrganik;
Servo servoAnorganik;

int pinOrganik = 18;
int pinAnorganik = 19;

void setup() {

  Serial.begin(115200);
  SerialBT.begin("ESP32_SAMPAH");

  Serial.println("ESP32 siap menerima perintah");

  servoOrganik.attach(pinOrganik);
  servoAnorganik.attach(pinAnorganik);

  servoOrganik.write(0);
  servoAnorganik.write(0);

}

void loop() {

  if (SerialBT.available()) {

    String cmd = SerialBT.readStringUntil('\n');
    cmd.trim();

    Serial.print("Perintah diterima: ");
    Serial.println(cmd);

    if (cmd == "organik") {

      Serial.println("Membuka sampah organik");

      servoOrganik.write(90);
      delay(3000);
      servoOrganik.write(0);

      Serial.println("Servo organik kembali");

    }

    else if (cmd == "anorganik") {

      Serial.println("Membuka sampah anorganik");

      servoAnorganik.write(90);
      delay(3000);
      servoAnorganik.write(0);

      Serial.println("Servo anorganik kembali");

    }

    else if (cmd == "tutup") {

      Serial.println("Menutup semua servo");

      servoOrganik.write(0);
      servoAnorganik.write(0);

    }

    else {

      Serial.println("Perintah tidak dikenal");

    }

  }

}
