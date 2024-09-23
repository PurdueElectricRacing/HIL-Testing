import utils
import os
import signal
import sys
import time
from pin_mapper import PinMapper
from hil_devices.hil_device import HilDevice
from hil_devices.serial_manager import SerialManager
from components.component import Component

from communication.can_bus import CanBus
from communication.daq_protocol import DaqProtocol
from communication.daq_protocol import DAQPin

""" HIL TESTER """

JSON_CONFIG_SCHEMA_PATH = ""
CONFIG_PATH = "../configurations"

NET_MAP_PATH = "../net_maps"
PIN_MAP_PATH = "../pin_maps"

PARAMS_PATH = "../hil_params.json"


class HIL():

    def __init__(self):
        utils.initGlobals()
        self.components = {}
        self.dut_connections = {}
        self.hil_devices = {}
        self.serial_manager = SerialManager()
        self.hil_params = utils.load_json_config(PARAMS_PATH, None)
        self.can_bus = None
        utils.hilProt = self
        signal.signal(signal.SIGINT, signal_int_handler)
        self.global_failed_checks = []
        self.global_test_names = []
        self.global_check_count = 0 # multiple checks within a test
        self.global_test_count = 0

    def init_can(self):
        config = self.hil_params
        self.daq_config = utils.load_json_config(os.path.join(config['firmware_path'], config['daq_config_path']), os.path.join(config['firmware_path'], config['daq_schema_path']))
        self.can_config = utils.load_json_config(os.path.join(config['firmware_path'], config['can_config_path']), os.path.join(config['firmware_path'], config['can_schema_path']))

        self.can_bus = CanBus(os.path.join(config['firmware_path'], config['dbc_path']), config['default_ip'], self.can_config)
        self.daq_protocol = DaqProtocol(self.can_bus, self.daq_config)

        self.can_bus.connect()
        self.can_bus.start()

    def load_pin_map(self, net_map, pin_map):
        net_map_f = os.path.join(NET_MAP_PATH, net_map)
        pin_map_f = os.path.join(PIN_MAP_PATH, pin_map)

        self.pin_map = PinMapper(net_map_f)
        self.pin_map.load_mcu_pin_map(pin_map_f)

    def clear_components(self):
        """ Reset HIL"""
        for c in self.components.values():
            c.shutdown()
        self.components = {}

    def clear_hil_devices(self):
        self.hil_devices = {}
        self.serial_manager.close_devices()

    def shutdown(self):
        self.clear_components()
        self.clear_hil_devices()
        self.stop_can()

        print(f"{utils.bcolors.OKCYAN}{utils.bcolors.UNDERLINE}")
        utils.log("TEST SUMMARY")
        print(f"{utils.bcolors.ENDC}")
        utils.log(f"{self.global_test_count} tests with {self.global_check_count} checks performed:")
        utils.log(', '.join(self.global_test_names))
        num_fail = len(self.global_failed_checks)
        num_pass = self.global_check_count - num_fail
        if (self.global_check_count == 0): 
            return
        utils.log(f"{num_pass}/{self.global_check_count} ({num_pass/self.global_check_count*100:.5}%) of checks passing")
        if (num_fail > 0):
            utils.log(f"{utils.bcolors.FAIL}{utils.bcolors.BOLD}Failing {num_fail} checks:{utils.bcolors.ENDC}")
            for c in self.global_failed_checks:
                utils.log(f"{c[0]} - {c[1]}")
        else:
            utils.log(f"{utils.bcolors.OKGREEN}{utils.bcolors.BOLD}ALL CHECKS PASSING{utils.bcolors.ENDC}")


    def stop_can(self):
        if not self.can_bus: return
        if self.can_bus.connected:
            self.can_bus.connected = False
            self.can_bus.join()
            # while(not self.can_bus.isFinished()):
            #     # wait for bus receive to finish
            #     pass
        self.can_bus.disconnect_bus()

    def load_config(self, config_name):
        config = utils.load_json_config(os.path.join(CONFIG_PATH, config_name), None) # TODO: validate w/ schema

        # TODO: support joining configs

        # Load hil_devices
        self.load_hil_devices(config['hil_devices'])

        # Setup corresponding components
        self.load_connections(config['dut_connections'])
    
    def load_connections(self, dut_connections):
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

    def add_component(self, board, net, mode):
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

    def load_hil_devices(self, hil_devices):
        self.clear_hil_devices()
        self.serial_manager.discover_devices()
        for hil_device in hil_devices:
            if self.serial_manager.port_exists(hil_device["id"]):
                self.hil_devices[hil_device['name']] = HilDevice(hil_device['name'], hil_device['type'], hil_device['id'], self.serial_manager)
            else:
                self.handle_error(f"Failed to discover HIL device {hil_device['name']} with id {hil_device['id']}")

    def get_hil_device(self, name):
        if name in self.hil_devices:
            return self.hil_devices[name]
        else:
            self.handle_error(f"HIL device {name} not recognized")

    def get_hil_device_connection(self, board, net):
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
    
    def din(self, board, net):
        return self.add_component(board, net, 'DI')
    
    def dout(self, board, net):
        return self.add_component(board, net, 'DO')

    def ain(self, board, net):
        return self.add_component(board, net, 'AI')
    
    def aout(self, board, net):
        return self.add_component(board, net, 'AO')
    
    def pot(self, board, net):
        return self.add_component(board, net, 'POT')

    def daq_var(self, board, var_name):
        try:
            return utils.signals[utils.b_str][board][f"daq_response_{board.upper()}"][var_name]
        except KeyError as e:
            self.handle_error(f"Unable to locate DAQ variable {var_name} of {board}")

    def can_var(self, board, message_name, signal_name):
        try:
            return utils.signals[utils.b_str][board][message_name][signal_name]
        except KeyError:
            self.handle_error(f"Unable to locate CAN signal {signal_name} of message {message_name} of board {board}")

    def mcu_pin(self, board, net):
        bank, pin = self.pin_map.get_mcu_pin(board, net)
        if bank == None:
            self.handle_error(f"Failed to get mcu pin for {board} net {net}")
        return DAQPin(net, board, bank, pin)

    def start_test(self, name):
        print(f"{utils.bcolors.OKCYAN}Starting {name}{utils.bcolors.ENDC}")
        self.curr_test = name
        self.curr_test_fail_count = 0
        self.curr_test_count = 0
        self.global_test_count = self.global_test_count + 1
        self.global_test_names.append(name)

    def check(self, stat, check_name):
        stat_str = "PASS" if stat else "FAIL"
        stat_clr = utils.bcolors.OKGREEN if stat else utils.bcolors.FAIL
        print(f"{self.curr_test + ' - ' + check_name:<50}: {stat_clr+'['+stat_str+']'+utils.bcolors.ENDC:>10}")
        if (not stat): 
            self.curr_test_fail_count = self.curr_test_fail_count + 1
            self.global_failed_checks.append((self.curr_test,check_name))
        self.curr_test_count = self.curr_test_count + 1
        self.global_check_count = self.global_check_count + 1
        return stat

    def check_within(self, val1, val2, thresh, check_name):
        self.check(abs(val1 - val2) <= thresh, check_name)

    def end_test(self):
        print(f"{utils.bcolors.OKCYAN}{self.curr_test} failed {self.curr_test_fail_count} out of {self.curr_test_count} checks{utils.bcolors.ENDC}")

    def handle_error(self, msg):
        utils.log_error(msg)
        self.shutdown()
        exit(0)

def signal_int_handler(signum, frame):
    utils.log("Received signal interrupt, shutting down")
    if (utils.hilProt):
        utils.hilProt.shutdown()
    sys.exit(0)

if __name__ == "__main__":
    hil = HIL()
    hil.load_config("config_test.json")
