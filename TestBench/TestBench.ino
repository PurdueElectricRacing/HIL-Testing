#include <FlexCAN_T4.h>
#include <Arduino.h>
#include <Wire.h>


#define SERIAL_BAUDRATE 115200
const int TESTER_ID = 1;


// #define STM32
#ifdef STM32
	#define SERIAL_CON SerialUSB
	#define HAL_DAC_MODULE_ENABLED 1
#else
	#define SERIAL_CON Serial
#endif


#define DAC_EN
#define DIGIPOT_EN
#define CAN_EN


#ifdef STM32
	#ifdef DAC_EN
		#warning "Can't have both DAC_EN and STM32 enabled"
	#endif
#endif

#ifdef DAC_EN
	#include "Adafruit_MCP4706.h"
	
	#define NUM_DACS 8
	#define DAC_WIRE Wire
	#define DAC_SDA 17
	#define DAC_SCL 24

	Adafruit_MCP4706 dacs[NUM_DACS];
	bool dac_power_down[NUM_DACS];
#endif

#ifdef DIGIPOT_EN
	#include "SW_MCP4017.h"
	
	#define DIGIPOT_1_WIRE Wire1
	#define DIGIPOT_1_SDA 25
	#define DIGIPOT_1_SCL 16

	#define DIGIPOT_2_WIRE Wire2
	#define DIGIPOT_2_SDA 18
	#define DIGIPOT_2_SCL 19

	const uint8_t DIGIPOT_MAX_STEPS = 128;
	const float DIGIPOT_MAX_OHMS = 10000;

	MCP4017 digipot1(DIGIPOT_MAX_STEPS, DIGIPOT_MAX_OHMS);
	MCP4017 digipot2(DIGIPOT_MAX_STEPS, DIGIPOT_MAX_OHMS);
#endif

#ifdef CAN_EN
	#include <FlexCAN_T4.h>

	#define CAN_BAUDRATE 500000
	#define CAN_RX RX_SIZE_256
	#define CAN_TX TX_SIZE_16

	#define CAN_RESPONSE_NO_MESSAGE 0x01
	#define CAN_RESPONSE_FOUND      0x02
	#define CAN_IGNORE_ID           0xFF

	FlexCAN_T4<CAN1, CAN_RX, CAN_TX> vCan; // id: 1
	FlexCAN_T4<CAN3, CAN_RX, CAN_TX> mCan; // id: 2
#endif


enum GpioCommand {
	READ_ADC   = 0, 
	READ_GPIO  = 1, 
	WRITE_DAC  = 2, 
	WRITE_GPIO = 3,
	READ_ID    = 4,
	WRITE_POT  = 5,
	READ_CAN   = 6,
	WRITE_CAN  = 7
};

int TO_READ[] = { // Parrallel to GpioCommand
	2, // READ_ADC - command, pin
	2, // READ_GPIO - command, pin
	3, // WRITE_DAC - command, pin, value
	3, // WRITE_GPIO - command, pin, value
	1, // READ_ID - command
	3, // WRITE_POT - command, pin, value
	5, // READ_CAN - command, bus, ignore id, id bit 1, id bit 2
	13 // WRITE_CAN - command, bus, id bit 1, id bit 2, len, data (8 bytes)
};

// 13 = max(TO_READ)
uint8_t data[13] = { 0 };
int data_index = 0;
bool data_ready = false;


void setup() {
	SERIAL_CON.begin(SERIAL_BAUDRATE);

	#ifdef DAC_EN
		DAC_WIRE.setSDA(DAC_SDA);
		DAC_WIRE.setSCL(DAC_SCL);

		for (int i = 0; i < NUM_DACS; i++) {
			uint8_t addr = 0x60 + i;
			dacs[i].begin(addr, DAC_WIRE);

			dacs[i].setMode(MCP4706_PWRDN_500K);
			dac_power_down[i] = true; // start with power down
		}
	#endif

	#ifdef DIGIPOT_EN
		DIGIPOT_1_WIRE.setSDA(DIGIPOT_1_SDA);
		DIGIPOT_1_WIRE.setSCL(DIGIPOT_1_SCL);
		digipot1.begin(MCP4017ADDRESS, DIGIPOT_1_WIRE);

		DIGIPOT_2_WIRE.setSDA(DIGIPOT_2_SDA);
		DIGIPOT_2_WIRE.setSCL(DIGIPOT_2_SCL);
		digipot2.begin(MCP4017ADDRESS, DIGIPOT_2_WIRE);
	#endif

	#ifdef CAN_EN
		vCan.begin();
		vCan.setBaudRate(CAN_BAUDRATE);
		vCan.enableFIFO();

		mCan.begin();
		mCan.setBaudRate(CAN_BAUDRATE);
		mCan.enableFIFO();
	#endif
}

void error(String error_string) {
	SERIAL_CON.write(0xFF);
	SERIAL_CON.write(0xFF);
	SERIAL_CON.println(error_string);
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
				SERIAL_CON.write((val >> 8) & 0xFF);
				SERIAL_CON.write(val & 0xFF);
			} else {
				error("ADC PIN COUNT EXCEEDED");
			}
			break;
		}
		case GpioCommand::READ_GPIO: {
			int pin = data[1];
			#ifdef DAC_EN
				if (pin >= 200 && pin < 200 + NUM_DACS) {
					int dac_idx = pin - 200;
					dacs[dac_idx].setMode(MCP4706_PWRDN_500K);
					dac_power_down[dac_idx] = true;
					SERIAL_CON.write(0x01);
				} else
			#endif
				{
					pinMode(pin, INPUT);
					int val = digitalRead(pin);
					SERIAL_CON.write(val & 0xFF);
				}
			break;
		}
		case GpioCommand::WRITE_DAC: {
			int pin = data[1];
			uint8_t value = data[2];
			#ifdef DAC_EN
				int dac_idx = pin - 200;
				if (dac_idx >= 0 && dac_idx < NUM_DACS) {
					if (dac_power_down[dac_idx]) {
						dacs[dac_idx].setMode(MCP4706_AWAKE);
						dac_power_down[dac_idx] = false;
					}
					dacs[dac_idx].setVoltage(value);
				}
			#endif
			#ifdef STM32
				// 4 and 5 have DACs on f407
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
			SERIAL_CON.write(TESTER_ID);
			break;
		}
		case GpioCommand::WRITE_POT: {
			int pin = data[1];
			uint8_t value = data[2];
			#ifdef DIGIPOT_EN
				if (pin == 1) {
					digipot1.setSteps(value);
				} else if (pin == 2) {
					digipot2.setSteps(value); 
				} else
			#endif
				{
					error("POT PIN COUNT EXCEEDED");
				}
			break;
		}
		case GpioCommand::READ_CAN: {
			int bus = data[1];
			uint8_t ignore_id = data[2];
			uint32_t id = (data[3] << 8) | data[4]; // 11-bit ID
			#ifdef CAN_EN
				CAN_message_t msg = { 0 };
				bool found = false;

				if (bus == 1) {
					while (vCan.read(msg)) {
						if (msg.id == id || ignore_id == CAN_IGNORE_ID) { found = true; break; }
					}
				} else if (bus == 2) {
					while (mCan.read(msg)) {
						if (msg.id == id || ignore_id == CAN_IGNORE_ID) { found = true; break; }
					}
				} else {
					error("CAN BUS NOT SUPPORTED");
				}

				if (found) {
					SERIAL_CON.write(CAN_RESPONSE_FOUND);
					SERIAL_CON.write((uint8_t *)&msg.id, 4);
					SERIAL_CON.write(msg.len);
					SERIAL_CON.write(msg.buf, 8);
				} else {
					SERIAL_CON.write(CAN_RESPONSE_NO_MESSAGE);
				}
			#else
				error("CAN NOT ENABLED");
			#endif
			break;
		}
		case GpioCommand::WRITE_CAN: {
			int bus = data[1];
			#ifdef CAN_EN
				CAN_message_t msg = { 0 };
				msg.id = (data[2] << 8) | data[3]; // 11-bit ID
				msg.len = data[4];
				memcpy(msg.buf, &data[5], msg.len);

				msg.len = 8;
				msg.edl = 0;
				msg.brs = 0;
				msg.esi = 0;
				msg.flags.extended = false; 

				if (bus == 1) {
					vCan.write(msg);
				} else if (bus == 2) {
					mCan.write(msg);
				} else {
					error("CAN BUS NOT SUPPORTED");
				}
			#else
				error("CAN NOT ENABLED");
			#endif
			break;
		}
	} else {
		if (SERIAL_CON.available() > 0) {
			data[data_index] = SERIAL_CON.read();
			data_index++;

			uint8_t command = data[0];
			if (data_index == TO_READ[command]) {
				data_ready = true;
			}
		}
	}
}
