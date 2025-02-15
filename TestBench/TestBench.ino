
#include <Arduino.h>
#include "MCP4021.h"

// #define STM32
#ifdef STM32
	#define SERIAL SerialUSB
	#define HAL_DAC_MODULE_ENABLED 1
#else
	#define SERIAL Serial
#endif

const int TESTER_ID = 1;

#define DAC

#ifdef STM32
	#ifdef DAC
		#warning "Can't have both DAC and STM32 enabled"
	#endif
#endif

#ifdef DAC
	#include "Adafruit_MCP4706.h"
	#define NUM_DACS 8

	Adafruit_MCP4706 dacs[NUM_DACS];

	// DFRobot_MCP4725 dacs[NUM_DACS];
	// uint8_t dac_power_down[NUM_DACS];
#endif

#define DIGIPOT_EN
#ifdef DIGIPOT_EN
	const uint8_t DIGIPOT_UD_PIN  = 7;
	const uint8_t DIGIPOT_CS1_PIN = 22; // A4
	const uint8_t DIGIPOT_CS2_PIN = 23; // A5

	MCP4021 digipot1(DIGIPOT_CS1_PIN, DIGIPOT_UD_PIN, false);  // initialize Digipot 1
	MCP4021 digipot2(DIGIPOT_CS2_PIN, DIGIPOT_UD_PIN, false);  // initialize Digipot 2
#endif

enum GpioCommand {
	READ_ADC   = 0, 
	READ_GPIO  = 1, 
	WRITE_DAC  = 2, 
	WRITE_GPIO = 3,
	READ_ID    = 4,
	WRITE_POT  = 5,
};

int TO_READ[] = { // Parrallel to GpioCommand
	2, // READ_ADC - command, pin
	2, // READ_GPIO - command, pin
	3, // WRITE_DAC - command, pin, value
	3, // WRITE_GPIO - command, pin, value
	1, // READ_ID - command
	3, // WRITE_POT - command, pin, value
};

// 4 = max(TO_READ)
uint8_t data[4] = {-1, -1, -1, -1};
int data_index = 0;
bool data_ready = false;


void setup() {
	SERIAL.begin(115200);

#ifdef DAC
	// dacs[0].init(0x62, dac_vref);
	// dacs[1].init(0x63, dac_vref);
	// dacs[0].setMode(MCP4725_POWER_DOWN_500KRES);
	// dacs[1].setMode(MCP4725_POWER_DOWN_500KRES);
	// dac_power_down[0] = 1;
	// dac_power_down[1] = 1;

	for (int i = 0; i < NUM_DACS; i++) {
		uint8_t addr = 0x60 + i;
		dacs[i].begin(addr);
	}
#endif

#ifdef DIGIPOT_EN
	// Setting up Digipot 1
	digipot1.setup();
	digipot1.begin();

	// Setting up Digipot 2
	digipot2.setup();
	digipot2.begin();
#endif
}

void error(String error_string) {
	SERIAL.write(0xFF);
	SERIAL.write(0xFF);
	SERIAL.println(error_string);
}


void loop() {
	if (data_ready) {
		data_ready = false;
		data_index = 0;

		GpioCommand command = (GpioCommand) data[0];

		switch (command) {
		case GpioCommand::READ_ADC: {
			int pin = data[1];
			// if (pin <= ANALOG_PIN_COUNT)
			if (1) {
				int val = analogRead(pin);
				SERIAL.write((val >> 8) & 0xFF);
				SERIAL.write(val & 0xFF);
			} else {
				error("ADC PIN COUNT EXCEEDED");
			}
			break;
		}
		case GpioCommand::READ_GPIO: {
			int pin = data[1];
			// #ifdef DAC
			// 	if (pin >= 200 && pin < 200 + NUM_DACS) {
			// 		dacs[pin - 200].setMode(MCP4725_POWER_DOWN_500KRES);
			// 		dac_power_down[pin - 200] = 1;
			// 		SERIAL.write(0x01);
			// 	} else
			// #endif
				{
					pinMode(pin, INPUT);
					int val = digitalRead(pin);
					SERIAL.write(val & 0xFF);
				}
			break;
		}
		case GpioCommand::WRITE_DAC: {
			int pin = data[1];
			uint8_t value = data[2];
			// int value = (data[2] << 8) | data[3];
			#ifdef DAC
				if (pin >= 200 && pin < 200 + NUM_DACS) {
					// if (dac_power_down[pin-200]) {
					// 	dacs[pin-200].setMode(MCP4725_NORMAL_MODE);
					// 	dac_power_down[pin - 200] = 0;
					// }
					// dacs[pin - 200].outputVoltage(value);
					int dac_pin = pin - 200;
					dacs[dac_pin].setVoltage(value);
				}
			#endif
			#ifdef STM32
				// 4 and 5 have DAC on f407
				pinMode(pin, OUTPUT);
				analogWrite(pin, value & 0xFF); // max val 255
			#endif

			break;
		}
		case GpioCommand::WRITE_GPIO: {
			int pin = data[1];
			int value = data[2];
			pinMode(pin, OUTPUT);
			digitalWrite(pin, value);
			break;
		}
		case GpioCommand::READ_ID: {
			SERIAL.write(TESTER_ID);
			break;
		}
		case GpioCommand::WRITE_POT: {
			int pin = data[1];
			int value = data[2];
			#ifdef DIGIPOT_EN
				if (pin == 1) {
					digipot1.setTap((uint8_t) value);
				} else if (pin == 2) {
					digipot2.setTap((uint8_t) value); 
				} else
			#endif
				{
					error("POT PIN COUNT EXCEEDED");
				}
			break;
		}
		}
	} else {
		if (SERIAL.available() > 0) {
			data[data_index] = SERIAL.read();
			data_index++;

			uint8_t command = data[0];
			if (data_index == TO_READ[command]) {
				data_ready = true;
			}
		}
	}
}
