#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <ESPmDNS.h>

const char* ssid = "ilham";
const char* password = "12345678";

WebServer server(80);

Servo servoSAMPAH;

const int PIN_SERVO_SAMPAH = 19;

const int SERVO_OPEN_ANGLE = 0;
const int SERVO_CLOSE_ANGLE = 90;
const int SERVO_OPEN_2_ANGLE = 180;
const unsigned long SERVO_OPEN_DURATION_MS = 3000;

// state non-blocking
bool sampahActive = false;
unsigned long sampahStartTime = 0;

void closeOrganikIfNeeded() {
  if (sampahActive && millis() - sampahStartTime >= SERVO_OPEN_DURATION_MS) {
    servoSAMPAH.write(SERVO_CLOSE_ANGLE);
    sampahActive = false;
    Serial.println("Organik servo closed");
  }
}

void closeAnorganikIfNeeded() {
  if (sampahActive && millis() - sampahStartTime >= SERVO_OPEN_DURATION_MS) {
    servoSAMPAH.write(SERVO_CLOSE_ANGLE);
    sampahActive = false;
    Serial.println("Anorganik servo closed");
  }
}

void handleRoot() {
  server.send(200, "text/plain", "ESP32 server is running");
}

void handleOrganik() {
  Serial.println("CMD: ORGANIK");
  servoSAMPAH.write(SERVO_OPEN_ANGLE);
  sampahStartTime = millis();
  sampahActive = true;

  server.send(200, "application/json", "{\"status\":\"ok\",\"cmd\":\"organik\"}");
}

void handleAnorganik() {
  Serial.println("CMD: ANORGANIK");
  servoSAMPAH.write(SERVO_OPEN_2_ANGLE);
  sampahStartTime = millis();
  sampahActive = true;

  server.send(200, "application/json", "{\"status\":\"ok\",\"cmd\":\"anorganik\"}");
}

void setup() {
  Serial.begin(115200);

  servoSAMPAH.attach(PIN_SERVO_SAMPAH);

  servoSAMPAH.write(SERVO_CLOSE_ANGLE);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("Connected to WiFi");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  if (MDNS.begin("esp32")) {
    Serial.println("mDNS started: http://esp32.local");
  } else {
    Serial.println("mDNS failed, use IP address instead");
  }

  server.on("/", handleRoot);
  server.on("/organik", HTTP_GET, handleOrganik);
  server.on("/anorganik", HTTP_GET, handleAnorganik);

  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();

  closeOrganikIfNeeded();
  closeAnorganikIfNeeded();
}
