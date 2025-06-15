import os
import time
from typing import Optional
from hil.hil_devices.serial_manager import SerialManager

import hil.utils as utils

HIL_CMD_READ_ADC   = 0 # command, pin
HIL_CMD_READ_GPIO  = 1 # command, pin
HIL_CMD_WRITE_DAC  = 2 # command, pin, value (2 bytes)
HIL_CMD_WRITE_GPIO = 3 # command, pin, value
HIL_CMD_READ_ID    = 4 # command
HIL_CMD_WRITE_POT  = 5 # command, pin, value
HIL_CMD_READ_CAN   = 6 # command, bus, id bit 1, id bit 2

CAN_RESPONSE_NO_MESSAGE = 0x01
CAN_RESPONSE_FOUND      = 0x02

SERIAL_MASK = 0xFF # 2^8 - 1
SERIAL_BITS = 8 # char

HIL_DEVICES_PATH = os.path.join("..", "hil", "hil_devices")


class HilDevice():
    def __init__(self, name: str, type: str, id: int, serial_manager: SerialManager):
        self.name: str = name
        self.type: str = type
        self.id: int = id
        self.sm: SerialManager = serial_manager

        self.config: dict = utils.load_json_config(os.path.join(HIL_DEVICES_PATH, f"hil_device_{self.type}.json"), None) # TODO: validate w/ schema

        self.adc_to_volts: dict[int, float] = {
            5: 0.0,
            24: 0.0,
        }
        self.adc_max: int = 0
        if "adc_config" in self.config:
            self.adc_max = pow(2, self.config['adc_config']['bit_resolution']) - 1
            # Note: Xv looks like xv_reference_v due to voltage divider
            self.adc_to_volts[5]  = (5.0  / self.config['adc_config']['5v_reference_v'])  * self.config['adc_config']['reference_v'] / self.adc_max
            self.adc_to_volts[24] = (24.0 / self.config['adc_config']['24v_reference_v']) * self.config['adc_config']['reference_v'] / self.adc_max
            
        self.volts_to_dac: float = 0.0
        self.dac_max: int = 0
        if "dac_config" in self.config:
            self.dac_max = pow(2, self.config['dac_config']['bit_resolution']) - 1
            self.volts_to_dac = self.dac_max / float(self.config['dac_config']['reference_v']) 
        
        self.pot_max:int = 0
        if "pot_config" in self.config:
            self.pot_max = pow(2, self.config['pot_config']['bit_resolution']) - 1

    def get_port_number(self, port_name: str, mode: str) -> int:
        for p in self.config['ports']:
            if port_name == p['name']:
                    if mode == p['mode']:
                        return p['port']
                    else:
                        utils.log_warning(f"Port {port_name} on {self.name} does not have capability {mode}")
                        utils.log_warning(f"Ports with {mode} capability for {self.name} include:")
                        utils.log_warning([p['name'] for p in self.config['ports'] if mode == p['mode']])
                        utils.log_warning("Change connection and try again.")
                        return -1
        for m in self.config['muxs']:
            if port_name.startswith(m['name']):
                if mode == m['mode']:
                    return m['port']
                else:
                    utils.log_warning(f"Mux named {m['name']} on {self.name} does not have capability {mode}")
                    return -1
        for c in self.config['can']:
            if port_name.startswith(c['name']):
                if mode == "CAN":
                    return c['port']
                else:
                    utils.log_warning(f"CAN bus named {c['name']} on {self.name} does not have capability {mode}")
                    return -1
        utils.log_error(f"Port {port_name} not found for hil device {self.name}")
        return -1
    
    def get_mux_info(self, port_name: str) -> tuple[int, int, list[int], str]:
        """
            Returns: mux_select, mux_read_port, mux_select_ports, mode.
            port_name = f"{mux_name}_{mux_select}" (ex: "24vMUX_13")
        """
        name_parts = port_name.split('_')
        if len(name_parts) != 2:
            utils.log_error(f"Invalid mux port name {port_name} for {self.name}")
            return (-1, -1, [], "")
        try:
            mux_select = int(name_parts[1])
        except ValueError:
            utils.log_error(f"Invalid mux select value {name_parts[1]} for {self.name}")
            return (-1, -1, [], "")
    
        mux_name = name_parts[0]
        for m in self.config['muxs']:
            if m['name'] == mux_name:
                return (mux_select, m['port'], m['pins'], m['mode'])
            
    def get_can_info(self, port_name: str) -> tuple[int, int]:
        """
            Returns: can_bus, can_message_id.
            port_name = f"{can_name}_{can_message_id}" (ex: "CAN1_123")
        """
        name_parts = port_name.split('_')
        if len(name_parts) != 2:
            utils.log_error(f"Invalid CAN port name {port_name} for {self.name}")
            return (-1, -1)
        try:
            can_id = int(name_parts[1])
        except ValueError:
            utils.log_error(f"Invalid CAN id value {name_parts[1]} for {self.name}")
            return (-1, -1)
    
        can_name = name_parts[0]
        for c in self.config['can']:
            if c['name'] == can_name:
                return (c['port'], can_id)
        
        utils.log_error(f"CAN bus {can_name} not found for {self.name}")
        return (-1, -1)

    def write_gpio(self, pin: int, value: int) -> None: 
        data = [(HIL_CMD_WRITE_GPIO & SERIAL_MASK), (pin & SERIAL_MASK), value]
        self.sm.send_data(self.id, data)

    def write_dac(self, pin: int, voltage: float) -> None:
        value = int(voltage * self.volts_to_dac)
        data = [(HIL_CMD_WRITE_DAC & SERIAL_MASK), (pin & SERIAL_MASK), value]
        self.sm.send_data(self.id, data)

    def read_gpio(self, pin: int) -> int:
        data = [(HIL_CMD_READ_GPIO & SERIAL_MASK), (pin & SERIAL_MASK)]
        self.sm.send_data(self.id, data)
        d = self.sm.read_data(self.id, 1)
        if len(d) == 1:
            d = int.from_bytes(d, "big")
            if (d <= 1): return d
        utils.log_error(f"Failed to read gpio pin {pin} on {self.name}")

    def read_analog(self, pin: int, v_mode: int) -> float:
        data = [(HIL_CMD_READ_ADC & SERIAL_MASK), (pin & SERIAL_MASK)]
        self.sm.send_data(self.id, data)
        d = self.sm.read_data(self.id, 2)
        if len(d) == 2:
            d = int.from_bytes(d, "big")
            if (d <= self.adc_max): return (d * self.adc_to_volts[v_mode])
        utils.log_error(f"Failed to read adc pin {pin} on {self.name}")
        return 0

    def write_pot(self, pin: int, value: float) -> None:
        value = min(self.pot_max, max(0, int(value * self.pot_max)))
        data = [(HIL_CMD_WRITE_POT & SERIAL_MASK), (pin & SERIAL_MASK), value]
        self.sm.send_data(self.id, data)

    def read_mux(self, select: int, read_pin: int, select_pins: list[int], mode: str) -> float:
        if select >= 2**len(select_pins) or select < 0:
            raise ValueError("select out of range for given select_pins")

        for i, pin in enumerate(select_pins):
            bit = 1 if (select & (1 << i)) else 0
            self.write_gpio(pin, bit)
        time.sleep(0.01)
        
        if mode == "AI5":
            return self.read_analog(read_pin, 5)
        elif mode == "AI24":
            return self.read_analog(read_pin, 24)
        elif mode == "DI":
            return self.read_gpio(read_pin)
        else:
            utils.log_error(f"Unrecognized mux mode {mode} for {self.name}")
            return 0.0
        
    def read_can(self, bus: int, id: int) -> Optional[list[int]]:
        id_bit1 = (id >> 8) & SERIAL_MASK
        id_bit2 = id & SERIAL_MASK
        data = [(HIL_CMD_READ_CAN & SERIAL_MASK), (bus & SERIAL_MASK), id_bit1, id_bit2]
        self.sm.send_data(self.id, data)

        d_status = self.sm.read_data(self.id, 1)
        if len(d_status) != 1:
            utils.log_error(f"Failed to read reponse from CAN bus {bus} with id {id} on {self.name}")
            return []
        d_status = int.from_bytes(d_status, "big")

        if d_status == CAN_RESPONSE_NO_MESSAGE:
            return None
        elif d_status != CAN_RESPONSE_FOUND:
            utils.log_error(f"Unexpected CAN response {d_status} for bus {bus} with id {id} on {self.name}")
            return []
        
        d_len = self.sm.read_data(self.id, 1)
        if len(d_len) != 1:
            utils.log_error(f"Failed to read length of CAN message on bus {bus} with id {id} on {self.name}")
            return []
        d_len = int.from_bytes(d_len, "big")

        if d_len < 1 or d_len > 8:
            utils.log_error(f"Invalid CAN message length {d_len} for bus {bus} with id {id} on {self.name}")
            return []
        
        d = self.sm.read_data(self.id, d_len)
        if len(d) == d_len:
            return [int.from_bytes(d[i:i+1], "big") for i in range(d_len)]