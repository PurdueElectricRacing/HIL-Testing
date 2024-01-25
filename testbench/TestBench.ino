#define HAL_DAC_MODULE_ENABLED 1
#include <Arduino.h>
#include "DigiPot.h"

// #define DEBUG
//#define STM32
#ifdef STM32
#define SERIAL SerialUSB
#else
#define SERIAL Serial
#endif

const int TESTER_ID = 1;

//#define DIGIPOT_EN
const uint8_t DIGIPOT_UD_PIN  = 7;
const uint8_t DIGIPOT_CS1_PIN = 22; // A4
const uint8_t DIGIPOT_CS2_PIN = 23; // A5
digipot_t dp1, dp2;

int count = 0;
char data[3];

struct Command
{
  Command(uint8_t command=0, uint8_t pin=0, uint8_t value=0)
  {
    data[0] = command;
    data[1] = pin;
    data[2] = value;
  };

  void reinit(char data[])
  {
    this->data[0] = data[0];
    this->data[1] = data[1];
    this->data[2] = data[2];
  };

  uint8_t command() { return data[0];};
  uint8_t pin() { return data[1]; };
  uint16_t value() { 
    return data[2]; 
  };
  int size() { return 3 * sizeof(char); };
  char data[3];
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
  SERIAL.begin(115200);
#ifdef DIGIPOT_EN
  digipot_init(DIGIPOT_CS1_PIN, DIGIPOT_UD_PIN, &dp1);
  digipot_init(DIGIPOT_CS2_PIN, DIGIPOT_UD_PIN, &dp2);
  digipot_set(48, &dp1);
#endif
}

void error(String error_string)
{
  SERIAL.write(0xFF);
  SERIAL.write(0xFF);
  SERIAL.println(error_string);
}

void loop()
{
  if (SERIAL.available() >= 3)
  {
    data[0] = SERIAL.read();
    data[1] = SERIAL.read();
    data[2] = SERIAL.read();
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
          SERIAL.write(val & 0xFF);
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
          // 4 and 5 have DAC on f407
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
          SERIAL.write((val >> 8) & 0xFF);
          SERIAL.write(val & 0xFF);
        }
        else
        {
          error("ADC PIN COUNT EXCEEDED");
        }
        break;
      }
      case (READ_ID):
      {
        SERIAL.write(TESTER_ID);
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
