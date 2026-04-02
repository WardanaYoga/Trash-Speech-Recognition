/*
 * ============================================================
 *  ESP32 Servo Controller via Bluetooth Serial
 *  -------------------------------------------
 *  Perintah yang diterima:
 *    "organik"   → Servo ke KANAN  (0°)
 *    "anorganik" → Servo ke KIRI   (180°)
 *    "default"   → Servo ke TENGAH (90°)
 *
 *  Library yang dibutuhkan:
 *    - ESP32Servo  (install via Library Manager)
 *    - BluetoothSerial (sudah built-in di ESP32 Arduino Core)
 *
 *  Wiring:
 *    Servo Signal → GPIO 18
 *    Servo VCC    → 5V (atau VIN)
 *    Servo GND    → GND
 * ============================================================
 */

#include <BluetoothSerial.h>
#include <ESP32Servo.h>

// ── Konfigurasi ──────────────────────────────────────────────
#define SERVO_PIN      18      // Pin signal servo
#define POS_DEFAULT    90      // Posisi tengah (default)
#define POS_ORGANIK     0      // Posisi kanan  (organik)
#define POS_ANORGANIK  180     // Posisi kiri   (anorganik)
#define BT_DEVICE_NAME "ESP32_SampahSorter"
// ─────────────────────────────────────────────────────────────

BluetoothSerial SerialBT;
Servo myServo;

String inputBuffer = "";

void setup() {
  Serial.begin(115200);

  // Inisialisasi Bluetooth
  if (!SerialBT.begin(BT_DEVICE_NAME)) {
    Serial.println("[ERROR] Bluetooth gagal diinisialisasi!");
    while (true);
  }
  Serial.println("[INFO] Bluetooth aktif. Nama: " + String(BT_DEVICE_NAME));

  // Inisialisasi Servo
  ESP32PWM::allocateTimer(0);
  myServo.setPeriodHertz(50);          // Standar 50Hz untuk servo
  myServo.attach(SERVO_PIN, 500, 2400); // min/max pulse width (µs)
  goToDefault();

  Serial.println("[INFO] Servo siap di pin " + String(SERVO_PIN));
  Serial.println("[INFO] Menunggu perintah Bluetooth...");
}

void loop() {
  // Baca data dari Bluetooth jika tersedia
  while (SerialBT.available()) {
    char c = (char)SerialBT.read();

    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    } else {
      inputBuffer += c;
    }
  }

  // Juga baca dari Serial Monitor untuk debugging
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    } else {
      inputBuffer += c;
    }
  }
}

// ── Fungsi Pemrosesan Perintah ────────────────────────────────
void processCommand(String cmd) {
  cmd.trim();
  cmd.toLowerCase();

  Serial.println("[CMD] Diterima: " + cmd);

  if (cmd == "organik") {
    goToOrganik();
  } else if (cmd == "anorganik") {
    goToAnorganik();
  } else if (cmd == "default") {
    goToDefault();
  } else if (cmd == "status") {
    sendStatus();
  } else {
    String errMsg = "ERROR:perintah_tidak_dikenal:" + cmd;
    SerialBT.println(errMsg);
    Serial.println("[WARN] " + errMsg);
  }
}

// ── Fungsi Gerak Servo ────────────────────────────────────────
void goToOrganik() {
  myServo.write(POS_ORGANIK);
  delay(500); // Tunggu servo sampai posisi
  SerialBT.println("OK:organik:kanan:" + String(POS_ORGANIK));
  Serial.println("[SERVO] → Kanan (Organik) " + String(POS_ORGANIK) + "°");
}

void goToAnorganik() {
  myServo.write(POS_ANORGANIK);
  delay(500);
  SerialBT.println("OK:anorganik:kiri:" + String(POS_ANORGANIK));
  Serial.println("[SERVO] ← Kiri (Anorganik) " + String(POS_ANORGANIK) + "°");
}

void goToDefault() {
  myServo.write(POS_DEFAULT);
  delay(500);
  SerialBT.println("OK:default:tengah:" + String(POS_DEFAULT));
  Serial.println("[SERVO] — Tengah (Default) " + String(POS_DEFAULT) + "°");
}

void sendStatus() {
  int pos = myServo.read();
  String posLabel;
  if (pos <= 10)         posLabel = "organik(kanan)";
  else if (pos >= 170)   posLabel = "anorganik(kiri)";
  else                   posLabel = "default(tengah)";

  String statusMsg = "STATUS:posisi=" + String(pos) + ":" + posLabel;
  SerialBT.println(statusMsg);
  Serial.println("[STATUS] " + statusMsg);
}
