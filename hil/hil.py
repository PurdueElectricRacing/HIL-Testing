from types import FrameType
import hil.utils as utils
import os
import signal
import sys
from hil.pin_mapper import PinMapper
from hil.hil_devices.hil_device import HilDevice
from hil.hil_devices.serial_manager import SerialManager
from hil.components.component import Component

from hil.communication.can_bus import CanBus, BusSignal
from hil.communication.daq_protocol import DaqProtocol
from hil.communication.daq_protocol import DAQPin
from hil.communication.daq_protocol import DAQVariable

""" HIL TESTER """

JSON_CONFIG_SCHEMA_PATH = ""
CONFIG_PATH = os.path.join("..", "configurations")

NET_MAP_PATH = os.path.join("..", "net_maps")
PIN_MAP_PATH = os.path.join("..", "pin_maps")

PARAMS_PATH = os.path.join("..", "hil_params.json")

DAQ_CONFIG_PATH = os.path.join("common", "daq", "daq_config.json")
DAQ_SCHEMA_PATH = os.path.join("common", "daq", "daq_schema.json")
DBC_PATH = os.path.join("common", "daq", "per_dbc.dbc")
CAN_CONFIG_PATH = os.path.join("common", "daq", "can_config.json")
CAN_SCHEMA_PATH = os.path.join("common", "daq", "can_schema.json")
# FAULT_CONFIG_PATH = os.path.join("common", "faults", "fault_config.json")
# FAULT_SCHEMA_PATH = os.path.join("common", "faults", "fault_schema.json")


class HIL():
    def __init__(self):
        utils.initGlobals()
        self.components: dict[str, Component] = {}
        self.dut_connections: dict[str, dict[str, dict[str, tuple[str, str]]]] = {}
        self.hil_devices: dict[str, HilDevice] = {}
        self.serial_manager: SerialManager = SerialManager()
        self.hil_params: dict = utils.load_json_config(PARAMS_PATH, None)
        self.can_bus: CanBus = None
        utils.hilProt = self
        signal.signal(signal.SIGINT, signal_int_handler)

    def init_can(self):
        firmware_path = self.hil_params["firmware_path"]

        self.daq_config = utils.load_json_config(os.path.join(firmware_path, DAQ_CONFIG_PATH), os.path.join(firmware_path, DAQ_SCHEMA_PATH))
        self.can_config = utils.load_json_config(os.path.join(firmware_path, CAN_CONFIG_PATH), os.path.join(firmware_path, CAN_SCHEMA_PATH))

        self.can_bus = CanBus(os.path.join(firmware_path, DBC_PATH), self.hil_params["default_ip"], self.can_config)
        self.daq_protocol = DaqProtocol(self.can_bus, self.daq_config)

        self.can_bus.connect()
        self.can_bus.start()

    def load_pin_map(self, net_map: str, pin_map: str) -> None:
        net_map_f = os.path.join(NET_MAP_PATH, net_map)
        pin_map_f = os.path.join(PIN_MAP_PATH, pin_map)

        self.pin_map = PinMapper(net_map_f)
        self.pin_map.load_mcu_pin_map(pin_map_f)

    def clear_components(self) -> None:
        """ Reset HIL"""
        for c in self.components.values():
            c.shutdown()
        self.components = {}

    def clear_hil_devices(self) -> None:
        self.hil_devices = {}
        self.serial_manager.close_devices()

    def shutdown(self) -> None:
        self.clear_components()
        self.clear_hil_devices()
        self.stop_can()

    def stop_can(self) -> None:
        if not self.can_bus: return
        
        if self.can_bus.connected:
            self.can_bus.connected = False
            self.can_bus.join()
            # while(not self.can_bus.isFinished()):
            #     # wait for bus receive to finish
            #     pass
        self.can_bus.disconnect_bus()

    def load_config(self, config_name: str) -> None:
        config = utils.load_json_config(os.path.join(CONFIG_PATH, config_name), None) # TODO: validate w/ schema

        # TODO: support joining configs

        # Load hil_devices
        self.load_hil_devices(config['hil_devices'])

        # Setup corresponding components
        self.load_connections(config['dut_connections'])
    
    def load_connections(self, dut_connections: dict) -> None:
        self.dut_connections = {}
        # Dictionary format:
        # [board][connector][pin] = (hil_device, port)
        for board_connections in dut_connections:
            board_name = board_connections['board']
            if not board_name in self.dut_connections:
                self.dut_connections[board_name] = {}
            for c in board_connections['harness_connections']:
                connector = c['dut']['connector']
                pin = str(c['dut']['pin'])
                hil_port = (c['hil']['device'], c['hil']['port'])
                if not connector in self.dut_connections[board_name]:
                    self.dut_connections[board_name][connector] = {}
                self.dut_connections[board_name][connector][pin] = hil_port

    def add_component(self, board: str, net: str, mode: str) -> Component:
        # If board is a HIL device, net is expected to be port name
        # If board is a DUT device, net is expected to be a net name from the board
        if board in self.hil_devices:
            hil_con = (board, net)
        else:
            hil_con = self.get_hil_device_connection(board, net)
        comp_name = '.'.join([board, net])
        if not comp_name in self.components:
            comp = Component(comp_name, hil_con, mode, self)
            self.components[comp_name] = comp
        else:
            utils.log_warning(f"Component {comp_name} already exists")
        return self.components[comp_name]

    def load_hil_devices(self, hil_devices: dict) -> None:
        self.clear_hil_devices()
        self.serial_manager.discover_devices()
        for hil_device in hil_devices:
            if self.serial_manager.port_exists(hil_device["id"]):
                self.hil_devices[hil_device['name']] = HilDevice(hil_device['name'], hil_device['type'], hil_device['id'], self.serial_manager)
            else:
                self.handle_error(f"Failed to discover HIL device {hil_device['name']} with id {hil_device['id']}")

    def get_hil_device(self, name: str) -> HilDevice:
        if name in self.hil_devices:
            return self.hil_devices[name]
        else:
            self.handle_error(f"HIL device {name} not recognized")

    def get_hil_device_connection(self, board: str, net: str) -> tuple[str, str]:
        """ Converts dut net to hil port name """
        if not board in self.dut_connections:
            self.handle_error(f"No connections to {board} found in configuration.")
        board_cons = self.dut_connections[board]

        net_cons = self.pin_map.get_net_connections(board, net)
        for c in net_cons:
            connector = c[0]
            pin = c[1]
            if connector in board_cons:
                if pin in board_cons[connector]:
                    return board_cons[connector][pin]
        utils.log_warning(f"Unable to find dut connection to net {net} on board {board}")
        utils.log_warning(f"The net {net} is available on {board} via ...")
        utils.log_warning(net_cons)
        self.handle_error(f"Connect dut to {net} on {board}.")
    
    def din(self, board: str, net: str) -> Component:
        return self.add_component(board, net, 'DI')

    def dout(self, board: str, net: str) -> Component:
        return self.add_component(board, net, 'DO')
    
    def ain(self, board: str, net: str) -> Component:
        return self.add_component(board, net, 'AI')
    
    def aout(self, board: str, net: str) -> Component:
        return self.add_component(board, net, 'AO')
    
    def pot(self, board: str, net: str) -> Component:
        return self.add_component(board, net, 'POT')
    
    def daq_var(self, board: str, var_name: str) -> DAQVariable:
        try:
            return utils.signals[utils.b_str][board][f"daq_response_{board.upper()}"][var_name]
        except KeyError:
            self.handle_error(f"Unable to locate DAQ variable {var_name} of {board}")

    def can_var(self, board: str, message_name: str, signal_name: str) -> BusSignal:
        try:
            return utils.signals[utils.b_str][board][message_name][signal_name]
        except KeyError:
            self.handle_error(f"Unable to locate CAN signal {signal_name} of message {message_name} of board {board}")

    def mcu_pin(self, board: str, net: str) -> DAQPin:
        bank, pin = self.pin_map.get_mcu_pin(board, net)
        if bank == None:
            self.handle_error(f"Failed to get mcu pin for {board} net {net}")
        return DAQPin(net, board, bank, pin)

    def handle_error(self, msg: str) -> None:
        utils.log_error(msg)
        self.shutdown()
        exit(0)


def signal_int_handler(signum: int, frame: FrameType) -> None:
    utils.log("Received signal interrupt, shutting down")
    if utils.hilProt:
        utils.hilProt.shutdown()
    sys.exit(0)


# Old testing code. When run directly (python hil.py), this code will run.
# if __name__ == "__main__":
#     hil = HIL()
#     hil.load_config("config_test.json")
