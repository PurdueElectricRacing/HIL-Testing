import utils
import os
from hil_devices.hil_device_virtual import Virtual
from hil_devices.hil_device import HilDevice
from hil_devices.serial_manager import SerialManager
from components.component import Component
from components.sdc_node import SdcNode
from components.brake_transducer import BrakeTransducer

""" HIL TESTER """

JSON_CONFIG_SCHEMA_PATH = ""
CONFIG_PATH = "..\configurations"

class HIL():

    def __init__(self):
        utils.initGlobals()
        self.components = {}
        self.hil_devices = {}
        self.serial_manager = SerialManager()

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

    def load_config(self, config_name):
        config = utils.load_json_config(os.path.join(CONFIG_PATH, config_name), None) # TODO: validate w/ schema

        # Load hil_devices
        self.load_hil_devices(config['hil_devices'])

        # Setup corresponding components
        self.load_components(config['components'])


    def load_components(self, components):
        self.clear_components()
        for component in components:
            comp_type = component['type']
            if (comp_type == "Component"):
                self.components[component["name"]] = Component(component, self) 
            elif (comp_type == "SdcNode"):
                self.components[component["name"]] = SdcNode(component, self) 
            elif (comp_type == "BrakeTransducer"):
                self.components[component["name"]] = BrakeTransducer(component, self) 
            else:
                self.handle_error(f"Component {component['name']} has unrecognized type {comp_type}")

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

    def get_component(self, name):
        if name in self.components:
            return self.components[name]
        else:
            self.handle_error(f"Component {name} not recognized")

    def start_test(self, name):
        print(f"{utils.bcolors.OKCYAN}Starting {name}{utils.bcolors.ENDC}")
        self.curr_test = name
        self.curr_test_fail_count = 0
        self.curr_test_count = 0

    def check(self, stat, check_name):
        stat_str = "PASS" if stat else "FAIL"
        stat_clr = utils.bcolors.OKGREEN if stat else utils.bcolors.FAIL
        print(f"{self.curr_test} {check_name}: {stat_clr}[{stat_str}]{utils.bcolors.ENDC}")
        if (not stat): self.curr_test_fail_count = self.curr_test_fail_count + 1
        self.curr_test_count = self.curr_test_count + 1
        return stat

    def end_test(self):
        print(f"{utils.bcolors.OKCYAN}{self.curr_test} failed {self.curr_test_fail_count} out of {self.curr_test_count} checks{utils.bcolors.ENDC}")

    def handle_error(self, msg):
        utils.log_error(msg)
        self.shutdown()
        exit(0)

if __name__ == "__main__":
    hil = HIL()
    hil.load_config("config_test.json")
