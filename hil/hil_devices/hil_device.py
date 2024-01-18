import os
import time
import serial
import serial.tools.list_ports
import utils

HIL_CMD_LENGTH = 4
HIL_CMD_MASK   = 0x0F
HIL_CMD_READ_ADC   = 0
HIL_CMD_READ_GPIO  = 1
HIL_CMD_WRITE_DAC  = 2
HIL_CMD_WRITE_GPIO = 3
HIL_CMD_READ_ID    = 4

HIL_ID_LENGTH = 4
HIL_ID_MASK   = 0x0F

HIL_DAC_VREF = 5.0
HIL_DAC_PREC = 255

HIL_ADC_MAX = 1024
HIL_ADC_VREF = 5.0

HIL_DEVICES_PATH = "..\hil\hil_devices"

class HilDevice():

    def __init__(self, name, type, id, serial_manager):
        self.name = name
        self.type = type
        self.id = id
        self.sm = serial_manager

        self.config = utils.load_json_config(os.path.join(HIL_DEVICES_PATH, f"hil_device_{self.type}.json"), None) # TODO: validate w/ schema

    def get_port_number(self, port_name, mode):
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

    def write_gpio(self, pin, value): 
        data = [((HIL_CMD_WRITE_GPIO & HIL_CMD_MASK) << HIL_ID_LENGTH) | (pin & HIL_ID_MASK), value]
        self.sm.send_data(self.id, data)

    def write_dac(self, pin, value):
        value = int(value * HIL_DAC_PREC / HIL_DAC_VREF)
        data = [((HIL_CMD_WRITE_DAC & HIL_CMD_MASK) << HIL_ID_LENGTH) | (pin & HIL_ID_MASK), value]
        self.sm.send_data(self.id, data)

    def read_gpio(self, pin): 
        data = [((HIL_CMD_READ_GPIO & HIL_CMD_MASK) << HIL_ID_LENGTH) | (pin & HIL_ID_MASK), 0]
        self.sm.send_data(self.id, data)
        d = self.sm.read_data(self.id, 1)
        if len(d) == 1:
            d = int.from_bytes(d, "big")
            if (d <= 1): return d
        utils.log_error(f"Failed to read gpio pin {pin} on {self.name}")

    def read_analog(self, pin):
        data = [((HIL_CMD_READ_ADC & HIL_CMD_MASK) << HIL_ID_LENGTH) | (pin & HIL_ID_MASK), 0]
        self.sm.send_data(self.id, data)
        d = self.sm.read_data(self.id, 2)
        if len(d) == 2:
            d = int.from_bytes(d, "big")
            if (d <= HIL_ADC_MAX): return (d * HIL_ADC_VREF / HIL_ADC_MAX)
        utils.log_error(f"Failed to read adc pin {pin} on {self.name}")
        return 0
