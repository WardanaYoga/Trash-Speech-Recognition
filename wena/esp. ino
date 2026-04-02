#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <ESPmDNS.h>

const char* ssid = "aicenter";
const char* password = "aicenter";

WebServer server(80);

Servo servoOrganik;
Servo servoAnorganik;

const int PIN_SERVO_ORGANIK = 18;
const int PIN_SERVO_ANORGANIK = 19;

const int SERVO_OPEN_ANGLE = 90;
const int SERVO_CLOSE_ANGLE = 0;
const unsigned long SERVO_OPEN_DURATION_MS = 3000;

// state non-blocking
bool organikActive = false;
bool anorganikActive = false;
unsigned long organikStartTime = 0;
unsigned long anorganikStartTime = 0;

void closeOrganikIfNeeded() {
  if (organikActive && millis() - organikStartTime >= SERVO_OPEN_DURATION_MS) {
    servoOrganik.write(SERVO_CLOSE_ANGLE);
    organikActive = false;
    Serial.println("Organik servo closed");
  }
}

void closeAnorganikIfNeeded() {
  if (anorganikActive && millis() - anorganikStartTime >= SERVO_OPEN_DURATION_MS) {
    servoAnorganik.write(SERVO_CLOSE_ANGLE);
    anorganikActive = false;
    Serial.println("Anorganik servo closed");
  }
}

void handleRoot() {
  server.send(200, "text/plain", "ESP32 server is running");
}

void handleOrganik() {
  Serial.println("CMD: ORGANIK");
  servoOrganik.write(SERVO_OPEN_ANGLE);
  organikStartTime = millis();
  organikActive = true;

  server.send(200, "application/json", "{\"status\":\"ok\",\"cmd\":\"organik\"}");
}

void handleAnorganik() {
  Serial.println("CMD: ANORGANIK");
  servoAnorganik.write(SERVO_OPEN_ANGLE);
  anorganikStartTime = millis();
  anorganikActive = true;

  server.send(200, "application/json", "{\"status\":\"ok\",\"cmd\":\"anorganik\"}");
}

void setup() {
  Serial.begin(115200);

  servoOrganik.attach(PIN_SERVO_ORGANIK);
  servoAnorganik.attach(PIN_SERVO_ANORGANIK);

  servoOrganik.write(SERVO_CLOSE_ANGLE);
  servoAnorganik.write(SERVO_CLOSE_ANGLE);

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
