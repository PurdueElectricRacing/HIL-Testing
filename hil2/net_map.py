import csv

from . import hil_errors


# Board net pairing -------------------------------------------------------------------#
class BoardNet:
    """
    Represents a board/net combination in the net map (ex: 'Dashboard/BRK_STAT').
    Can be used as a key in a dictionary.
    """

    def __init__(self, board: str, net: str):
        """
        :param board: The name of the board (ex: 'Dashboard')
        :param net: The name of the net (ex: 'BRK_STAT')
        """
        self.board: str = board
        self.net: str = net

    def __hash__(self):
        return hash((self.board, self.net))

    def __eq__(self, other):
        return self.board == other.board and self.net == other.net

    def __neq__(self, other):
        return not (self == other)


# CSV entry ---------------------------------------------------------------------------#
class NetMapEntry:
    """Represents a row in the net map CSV file."""

    def __init__(self, board: str, net: str, component: str, designator: int):
        """
        :param board: The name of the board (ex: 'Dashboard')
        :param net: The name of the net (ex: 'BRK_STAT')
        :param component: The name of the component (ex: 'J3')
        :param designator: The designator number (ex: 9)
        """
        self.board = board
        self.net = net
        self.component = component
        self.designator = designator


# Net map -----------------------------------------------------------------------------#
class NetMap:
    def __init__(self, entries: dict[BoardNet, NetMapEntry]):
        """
        :param entries: A dictionary mapping board/net combinations to their net map
                        entries
        """
        self._entries: dict[BoardNet, NetMapEntry] = entries

    def get_entry(self, board: str, net: str) -> NetMapEntry:
        """
        Retrieves a net map entry by board and net name.

        :param board: The name of the board (ex: 'Dashboard')
        :param net: The name of the net (ex: 'BRK_STAT')
        :return: The net map entry for the specified board and net
        """
        board_net = BoardNet(board, net)
        if board_net in self._entries:
            return self._entries[board_net]
        else:
            raise hil_errors.ConnectionError(f"No net map entry found for: {board_net}")

    @classmethod
    def from_csv(cls, file_path: str) -> "NetMap":
        """
        Creates a NetMap instance from a CSV file.

        :param file_path: The path to the CSV file
        :return: A NetMap instance
        """
        entries = {}
        with open(file_path, newline="", encoding="utf-8") as net_map_file:
            reader = csv.DictReader(net_map_file)
            for row in reader:
                match row:
                    case {
                        "Board": board,
                        "Net": net,
                        "Component": component,
                        "Designator": designator_str,
                    }:
                        entry = NetMapEntry(
                            board=board,
                            net=net,
                            component=component,
                            designator=int(designator_str),
                        )
                        board_net = BoardNet(entry.board, entry.net)
                        entries[board_net] = entry
                    case _:
                        raise hil_errors.NetMapParseError(f"Invalid net map row: {row}")
        return cls(entries)
