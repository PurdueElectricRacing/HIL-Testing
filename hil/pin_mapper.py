#import utils
import os
#from hil_devices.hil_device import HilDevice
import csv
import utils

""" PIN MAPPER """

# TODO: support multiple MCU types

class PinMapper():

    def __init__(self, net_map):
        #utils.initGlobals()
        self.load_net_map(net_map)
        self.mcu_pin_map = {}
    
    def load_net_map(self, fname):
        self.net_map_fname = fname
        self.net_map = {}
        # CSV format:
        # Board,Net,Component,Designator,Connector Name,,
        # Create dictionary as follows
        # [board name][net name] = [(component, designator, connector name), ...]
        with open(self.net_map_fname, mode='r') as f:
            csv_file = csv.DictReader(f)
            for row in csv_file:
                board = row['Board']
                net = row['Net']
                items = (row['Component'], row['Designator'], row['Connector Name'])
                if not board in self.net_map:
                    self.net_map[board] = {}
                net_map_board = self.net_map[board]
                if not net in net_map_board:
                    net_map_board[net] = []
                self.net_map[board][net].append(items)
        
    def load_mcu_pin_map(self, fname):
        self.mcu_pin_name_fname = fname
        self.mcu_pin_map = {}
        # CSV format:
        # Designator,Pin Name,Type
        # Create dictionary as follows
        # [designator] = (bank, pin)
        with open(self.mcu_pin_name_fname, mode='r') as f:
            csv_file = csv.DictReader(f)
            for row in csv_file:
                if row['Type'] != 'I/O' or row['Pin Name'][0] != 'P':
                    continue
                designator = int(row['Designator'])
                bank = int(ord(row['Pin Name'][1]) - ord('A'))
                pin  = int(row['Pin Name'][2:])
                self.mcu_pin_map[designator] = (bank, pin)
        
    def get_mcu_pin(self, board, net):
        """ Returns first MCU pin found that is connected """
        connections = self.get_net_connections(board, net)
        for connection in connections:
            if connection[2] == 'MCU':
                designator = int(connection[1])
                if not designator in self.mcu_pin_map:
                    utils.log_error(f"Net {net} on board {board} on MCU designator {designator} is not a recognized I/O pin.")
                    return (None, None)
                return self.mcu_pin_map[designator]
        utils.log_error(f"Net {net} on board {board} is not connected to MCU.")
        return (None, None)

    def get_net_connections(self, board, net):
        """ [(component, designator, connector name), ...] """
        if not board in self.net_map:
            utils.log_error(f"Unrecogniazed board {board}.")
            return
        if not net in self.net_map[board]:
            utils.log_error(f"Unrecognized net {net} in board {board}.")
            return 
        return self.net_map[board][net]

    
if __name__ == "__main__":
    pm = PinMapper(os.path.join("..", "net_maps", "per_24_net_map.csv"))
    pm.load_mcu_pin_map(os.path.join("..", "pin_maps", "stm32f407_pin_map.csv"))

    print(pm.get_mcu_pin('ur mom', 'idk'))
    print(pm.get_mcu_pin('a_box', 'ur mom'))
    print(pm.get_mcu_pin('a_box', 'Isense_Ch1_raw'))
    print(pm.get_mcu_pin('a_box', 'GND'))
    print(pm.get_mcu_pin('a_box', 'ISense Ch1'))

 