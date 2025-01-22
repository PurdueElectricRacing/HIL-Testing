import os
from hil.hil_devices.serial_manager import SerialManager

import hil.utils as utils

HIL_CMD_READ_ADC   = 0 # command, pin
HIL_CMD_READ_GPIO  = 1 # command, pin
HIL_CMD_WRITE_DAC  = 2 # command, pin, value (2 bytes)
HIL_CMD_WRITE_GPIO = 3 # command, pin, value
HIL_CMD_READ_ID    = 4 # command
HIL_CMD_WRITE_POT  = 5 # command, pin, value

SERIAL_MASK = 0xFF # 2^8 - 1
SERIAL_BITS = 8 # char

HIL_DEVICES_PATH = "../hil/hil_devices"

class HilDevice():
    def __init__(self, name: str, type: str, id: int, serial_manager: SerialManager):
        self.name: str = name
        self.type: str = type
        self.id: int = id
        self.sm: SerialManager = serial_manager

        self.config = utils.load_json_config(os.path.join(HIL_DEVICES_PATH, f"hil_device_{self.type}.json"), None) # TODO: validate w/ schema

        self.rail_5v = 0
        if "calibrate_rail" in self.config and self.config['calibrate_rail']:
            # Measure 3V3 rail and find dac reference
            p = self.get_port_number('3v3ref', 'AI')
            if p >= 0:
                self.adc_to_volts = 1
                self.adc_max = pow(2, self.config['adc_config']['bit_resolution']) - 1
                meas_3v3 = self.read_analog(p)
                # 3.3V = meas_3v3 / adc_max * 5V
                # 5V = 3.3V * adc_max / meas_3v3
                self.rail_5v = 3.3 * self.adc_max / meas_3v3
                utils.log(f"5V rail measured to be {self.rail_5v:.3}V on {self.name}")

        self.adc_to_volts = 0.0
        self.adc_max = 0
        if "adc_config" in self.config:
            self.adc_max = pow(2, self.config['adc_config']['bit_resolution']) - 1
            if self.rail_5v == 0:
                self.adc_to_volts = float(self.config['adc_config']['reference_v']) / self.adc_max
            else:
                self.adc_to_volts = self.rail_5v / self.adc_max

        self.volts_to_dac = 0.0
        self.dac_max = 0
        if "dac_config" in self.config:
            self.dac_max = pow(2, self.config['dac_config']['bit_resolution']) - 1
            if self.rail_5v == 0:
                self.volts_to_dac = self.dac_max / float(self.config['dac_config']['reference_v']) 
            else:
                self.volts_to_dac = self.dac_max / self.rail_5v
        
        self.pot_max = 0
        if "pot_config" in self.config:
            self.pot_max = pow(2, self.config['pot_config']['bit_resolution']) - 1

    def get_port_number(self, port_name: str, mode: str) -> int:
        for p in self.config['ports']:
            if port_name == p['name']:
                    if mode in p['capabilities']:
                        return p['port']
                    else:
                        utils.log_warning(f"Port {port_name} on {self.name} does not have capability {mode}")
                        utils.log_warning(f"Ports with {mode} capability for {self.name} include:")
                        utils.log_warning([p['name'] for p in self.config['ports'] if mode in p['capabilities']])
                        utils.log_warning("Change connection and try again.")
                        return -1
        utils.log_error(f"Port {port_name} not found for hil device {self.name}")
        return -1

    def write_gpio(self, pin: int, value: int) -> None: 
        data = [(HIL_CMD_WRITE_GPIO & SERIAL_MASK), (pin & SERIAL_MASK), value]
        self.sm.send_data(self.id, data)

    def write_dac(self, pin: int, voltage: float) -> None:
        value = int(voltage * self.volts_to_dac)
        char_1 = (value >> SERIAL_BITS) & SERIAL_MASK
        char_2 = value & SERIAL_MASK
        data = [(HIL_CMD_WRITE_DAC & SERIAL_MASK), (pin & SERIAL_MASK), char_1, char_2]
        self.sm.send_data(self.id, data)

    def read_gpio(self, pin: int) -> int:
        data = [(HIL_CMD_READ_GPIO & SERIAL_MASK), (pin & SERIAL_MASK)]
        self.sm.send_data(self.id, data)
        d = self.sm.read_data(self.id, 1)
        if len(d) == 1:
            d = int.from_bytes(d, "big")
            if (d <= 1): return d
        utils.log_error(f"Failed to read gpio pin {pin} on {self.name}")

    def read_analog(self, pin: int) -> float:
        data = [(HIL_CMD_READ_ADC & SERIAL_MASK), (pin & SERIAL_MASK)]
        self.sm.send_data(self.id, data)
        d = self.sm.read_data(self.id, 2)
        if len(d) == 2:
            d = int.from_bytes(d, "big")
            if (d <= self.adc_max): return (d * self.adc_to_volts)
        utils.log_error(f"Failed to read adc pin {pin} on {self.name}")
        return 0

    def write_pot(self, pin: int, value: float) -> None:
        value = min(self.pot_max, max(0, int(value * self.pot_max)))
        data = [(HIL_CMD_WRITE_POT & SERIAL_MASK), (pin & SERIAL_MASK), value]
        self.sm.send_data(self.id, data)