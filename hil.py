import utils
import os
from emulators.emulator_virtual import Virtual
from components.sdc_node import SdcNode

""" HIL TESTER """

JSON_CONFIG_SCHEMA_PATH = ""
CONFIG_PATH = "configurations"
EMULATORS_PATH = "emulators"

class HIL():

    def __init__(self):
        self.components = {}
        self.emulators = {}

    def clear_components(self):
        """ Reset HIL"""
        # TODO: power down?
        self.components = {}

    def clear_emulators(self):
        self.emulators = {}

    def load_config(self, config_name):
        config = utils.load_json_config(os.path.join(CONFIG_PATH, config_name), None) # TODO: validate

        # Load emulators
        self.load_emulators(config['emulators'])

        # Setup corresponding components
        self.load_components(config['components'])

        print(self.emulators)
        print(self.components)

    def load_components(self, components):
        self.clear_components()

        # TODO: check valid
        for component in components:
            self.components[component["name"]] = eval(component["type"])(component, hil) # TODO: error check/handle eval fail

    def load_emulators(self, emulators):
        self.clear_emulators()
        for emulator in emulators:
            em_config = utils.load_json_config(os.path.join(EMULATORS_PATH, f"emulator_{emulator['type']}.json"))
            self.emulators[emulator["name"]] = eval(em_config['control_method'])(emulator['name'], em_config)

    def get_emulator(self, name):
        return self.emulators[name]

if __name__ == "__main__":
    hil = HIL()
    hil.load_config("config_dash.json")
