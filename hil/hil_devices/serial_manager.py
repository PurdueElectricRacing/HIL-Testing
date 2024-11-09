import serial
import serial.tools.list_ports
import time

class SerialManager():
    """ Manages hil device discovery and communication """

    def __init__(self):
        self.devices: dict[int, serial.Serial] = {}

    def discover_devices(self) -> None:
        # print([a[0] for  a in serial.tools.list_ports.comports()])
        ports = [a[0] for a in serial.tools.list_ports.comports() if ("Arduino" in a[1] or "USB Serial Device" in a[1])]
        self.devices = {}
        print('Arduinos found on ports ' + str(ports))
        for p in ports:
            ard = serial.Serial(p,115200, timeout=0.1, 
                                bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                xonxoff=0,
                                rtscts=0)
            ard.setDTR(False)
            time.sleep(1)
            ard.flushInput()
            ard.setDTR(True)
            # Uno takes a while startup, have to treat it nicely
            for _ in range(5):
                # Get Tester id
                ard.write(b'\x04\x00\x00')
                i = ard.read(1)
                if (len(i) == 1):
                    break
                time.sleep(1)
            if (len(i) == 1):
                self.devices[int.from_bytes(i, "big")] = ard
            else:
                print('Failed to receive tester id on port ' + str(p) + ' ' + str(i))
                ard.close()
        print('Tester ids: ' + str(list(self.devices.keys())))

    def port_exists(self, id: int) -> bool:
        return id in self.devices
    
    def send_data(self, id: int, data: list[int]) -> None:
        self.devices[id].write(data)

    def read_data(self, id: int, length: int) -> bytes:
        return self.devices[id].read(length)

    def close_devices(self) -> None:
        for d in self.devices.values():
            d.close()
