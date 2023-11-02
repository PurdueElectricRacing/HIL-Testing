from emulators.emulator import Emulator

class Virtual(Emulator):

    def __init__(self, name, config):
        super(Virtual, self).__init__(name, config)

    def register_output(self, port, type):
        print(f"{self.name}: registered port {port} as type {type}")
        return super().register_output(type)