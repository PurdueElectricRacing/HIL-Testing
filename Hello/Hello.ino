#include <Arduino.h>

int value = 0;

void setup() {
  Serial.begin(115200);
}

void loop() {
  value = !value;

  Serial.println("Value: " + String(value));

  pinMode(4, OUTPUT);
  digitalWrite(4, value);

  delay(3000);
}
