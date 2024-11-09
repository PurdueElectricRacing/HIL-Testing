#include <Arduino.h>

int value = 0;
int PIN = 3;

void setup() {
  Serial.begin(115200);
}

void loop() {
  value = !value;

  digitalWrite(LED_BUILTIN, value);

  Serial.println("Value: " + String(value));

  pinMode(PIN, OUTPUT);
  digitalWrite(PIN, value);

  delay(3000);
}
