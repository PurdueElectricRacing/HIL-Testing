
#include <Arduino.h>
#include "MCP4021.h"

// #define STM32
#ifdef STM32
	#define SERIAL SerialUSB
	#define HAL_DAC_MODULE_ENABLED 1
#else
	#define SERIAL Serial
#endif

const int TESTER_ID = 2;

#define DAC

#ifdef STM32
	#ifdef DAC
		#warning "Can't have both DAC and STM32 enabled"
	#endif
#endif

#ifdef DAC
	#include "DFRobot_MCP4725.h
	#define NUM_DACS 2

	DFRobot_MCP4725 dacs[NUM_DACS];
	uint8_t dac_power_down[NUM_DACS];
	const uint16_t dac_vref = 255;
#endif

#define DIGIPOT_EN
#ifdef DIGIPOT_EN
	const uint8_t DIGIPOT_UD_PIN  = 7;
	const uint8_t DIGIPOT_CS1_PIN = 22; // A4
	const uint8_t DIGIPOT_CS2_PIN = 23; // A5

	MCP4021 digipot1(DIGIPOT_CS1_PIN, DIGIPOT_UD_PIN, false);  // initialize Digipot 1
	MCP4021 digipot2(DIGIPOT_CS2_PIN, DIGIPOT_UD_PIN, false);  // initialize Digipot 2
#endif

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

	uint8_t command() { return data[0]; };
	uint8_t pin()     { return data[1]; };
	uint16_t value()  { return data[2]; };
	int size()        { return 3 * sizeof(char); };
	
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
	// Setting up Digipot 1
	digipot1.setup();
	digipot1.begin();

	// Setting up Digipot 2
	digipot2.setup();
	digipot2.begin();
#endif
#ifdef DAC
	dacs[0].init(0x63, dac_vref);
	dacs[1].init(0x62, dac_vref);
	dacs[0].setMode(MCP4725_POWER_DOWN_500KRES);
	dacs[1].setMode(MCP4725_POWER_DOWN_500KRES);
	dac_power_down[0] = 1;
	dac_power_down[1] = 1;
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
#ifdef DAC
				if (pin >= 200 && pin < 200 + NUM_DACS)
				{
					dacs[pin - 200].setMode(MCP4725_POWER_DOWN_500KRES);
					dac_power_down[pin - 200] = 1;
					SERIAL.write(0x01);
				}
				else
#endif
				{
					pinMode(pin, INPUT);
					int val = digitalRead(pin);
					SERIAL.write(val & 0xFF);
				}
				break;
			}
			case (WRITE_DAC):
			{
#ifdef DAC
				if (pin >= 200 && pin < 200 + NUM_DACS)
				{
					if (dac_power_down[pin-200])
					{
						dacs[pin-200].setMode(MCP4725_NORMAL_MODE);
						dac_power_down[pin - 200] = 0;
					}
					dacs[pin - 200].outputVoltage(value & 0xFF);
				}
#endif
#ifdef STM32
					// 4 and 5 have DAC on f407
					pinMode(pin, OUTPUT);
					analogWrite(pin, value & 0xFF); // max val 255
#endif
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
					digipot1.setTap((uint8_t) value);
				else if (pin == 2)
					digipot2.setTap((uint8_t) value); 
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
