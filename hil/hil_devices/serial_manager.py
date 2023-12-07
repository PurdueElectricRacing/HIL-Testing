import serial
import serial.tools.list_ports

class SerialManager():
    """ Manages hil device discovery and communication """

    def __init__(self):
        self.devices = {}

    def discover_devices(self):
        ports = [a[0] for a in serial.tools.list_ports.comports() if "Arduino" in a[1]]
        self.devices = {}
        print('Arduinos found on ports ' + str(ports))
        for p in ports:
            ard = serial.Serial(p,115200, timeout=.1)
            # Get Tester id
            ard.write(b'\x40\x00')
            i = ard.read(1)
            if (len(i) == 1):
                self.devices[int.from_bytes(i, "big")] = ard
            else:
                print('Failed to receive tester id on port ' + str(p))
                ard.close()
        print('Tester ids: ' + str(list(self.devices.keys())))

    def port_exists(self, id):
        return id in self.devices
    
    def send_data(self, id, data):
        self.devices[id].write(data)

    def read_data(self, id, length):
        return self.devices[id].read(length)

    def close_devices(self):
        for d in self.devices.values():
            d.close()
