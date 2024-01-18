#include <Arduino.h>
#include "DigiPot.h"

// #define DEBUG

const int DIGITAL_PIN_COUNT = 14;
const int ANALOG_PIN_COUNT = 5;

const int TESTER_ID = 0;

//#define DIGIPOT_EN
const uint8_t DIGIPOT_UD_PIN  = 7;
const uint8_t DIGIPOT_CS1_PIN = 22; // A4
const uint8_t DIGIPOT_CS2_PIN = 23; // A5
digipot_t dp1, dp2;

int count = 0;
char data[2];

struct Command
{
  Command(uint8_t command=0, uint8_t pin=0, uint8_t value=0)
  {
    data[0] = (command << 4) & 0xF0;
    data[0] |= (pin & 0x0F);
    data[1] = value;
  };

  void reinit(char data[])
  {
    this->data[0] = data[0];
    this->data[1] = data[1];
  };

  uint8_t command() { return (data[0] & 0xF0) >> 4; };
  uint8_t pin() { return data[0] & 0x0F; };
  uint16_t value() { 
    return data[1]; 
  };
  int size() { return 2 * sizeof(char); };
  char data[2];
};


enum GpioCommands
{
  READ_ADC   = 0, 
  READ_GPIO  = 1, 
  WRITE_DAC  = 2, 
  WRITE_GPIO = 3,
  READ_ID    = 4,
  WRITE_POT  = 5,
};


void setup()
{
  Serial.begin(115200);
#ifdef DIGIPOT_EN
  digipot_init(DIGIPOT_CS1_PIN, DIGIPOT_UD_PIN, &dp1);
  digipot_init(DIGIPOT_CS2_PIN, DIGIPOT_UD_PIN, &dp2);
  digipot_set(48, &dp1);
#endif
}

void error(String error_string)
{
  Serial.write(0xFF);
  Serial.write(0xFF);
  Serial.println(error_string);
}

void loop()
{
  if (Serial.available() >= 2)
  {
    data[0] = Serial.read();
    data[1] = Serial.read();
    Command c;
    c.reinit(data);
    count++;
    uint8_t command = c.command();
    uint8_t pin = c.pin();
    uint16_t value = c.value();

    switch (command)
    {
      case (WRITE_GPIO):
      {
        //if (pin < DIGITAL_PIN_COUNT)
        if (1)
        {
          pinMode(pin, OUTPUT);
          digitalWrite(pin, value);
        }
        else
        {
          error("GPIO PIN COUNT EXCEEDED");
        }
        break;
      }
      case (READ_GPIO):
      {
        //if (pin < DIGITAL_PIN_COUNT)
        if (1)
        {
          pinMode(pin, INPUT);
          int val = digitalRead(pin);
          Serial.write(val & 0xFF);
        }
        else
        {
          error("GPIO PIN COUNT EXCEEDED");
        }
        break;
      }
      case (WRITE_DAC):
      {
        //if (pin < DAC_PIN_COUNT)
        //{
          //mcp.analogWrite(pin, value);
          pinMode(pin, OUTPUT);
          analogWrite(pin, value & 0xFF); // max val 255
          // TODO: check valid PWM pin
        //}
        //else
        //{
        //  error("DAC PIN COUNT EXCEEDED");
        //}
        break;
      }
      case (READ_ADC):
      {
        //if (pin <= ANALOG_PIN_COUNT)
        if (1)
        {
          int val = analogRead(pin);
          Serial.write((val >> 8) & 0xFF);
          Serial.write(val & 0xFF);
        }
        else
        {
          error("ADC PIN COUNT EXCEEDED");
        }
        break;
      }
      case (READ_ID):
      {
        Serial.write(TESTER_ID);
        break;
      }
      case (WRITE_POT):
      {
#ifdef DIGIPOT_EN
        if (pin == 1)
          digipot_set((uint8_t) value, &dp1);
        else if (pin == 2)
          digipot_set((uint8_t) value, &dp2);
        else
#endif
        {
          error("POT PIN COUNT EXCEEDED");
        }
        break;
      }
    }
  }
}
