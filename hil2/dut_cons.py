import json

from . import hil_errors


# HIL DUT Connection ------------------------------------------------------------------#
class HilDutCon:
    """The HIL side of a DUT connection"""

    def __init__(self, device: str, port: str):
        """
        :param device: The name of the HIL device (ex: 'RearTester')
        :param port: The port name on the HIL device (ex: 'DO7')
        """
        self.device: str = device
        self.port: str = port

    @classmethod
    def from_json(cls, hil_dut_con: dict) -> "HilDutCon":
        """
        Create a HilDutCon instance from a JSON dictionary.

        :param hil_dut_con: The JSON dictionary representing the HIL DUT connection
        :return: A HilDutCon instance
        """
        match hil_dut_con:
            case {"device": device, "port": port}:
                return cls(device, port)
            case _:
                error_msg = f"Invalid HIL DUT connection configuration: {hil_dut_con}"
                raise hil_errors.ConfigurationError(error_msg)


# Test DUT Connection -----------------------------------------------------------------#
class DutCon:
    """The tested side of a DUT connection"""

    def __init__(self, connector: str, pin: int):
        """
        :param connector: The name of the DUT connector (ex: 'J3')
        :param pin: The pin number on the DUT connector (ex: 9)
        """
        self.connector: str = connector
        self.pin: int = pin

    @classmethod
    def from_json(cls, dut_con: dict) -> "DutCon":
        """
        Create a DutCon instance from a JSON dictionary.

        :param dut_con: The JSON dictionary representing the DUT connection
        :return: A DutCon instance
        """
        match dut_con:
            case {"connector": connector, "pin": pin}:
                return cls(connector, pin)
            case _:
                error_msg = f"Invalid DUT connection configuration: {dut_con}"
                raise hil_errors.ConfigurationError(error_msg)


# DUT Board Connections ---------------------------------------------------------------#
class DutBoardCons:
    def __init__(self, harness_connections: dict[DutCon, HilDutCon]):
        """
        :param harness_connections: A dictionary mapping DUT connections to HIL connections
        """
        self._harness_connections: dict[DutCon, HilDutCon] = harness_connections

    @classmethod
    def from_json(cls, harness_connections: list[dict]) -> "DutBoardCons":
        """
        Create a DutBoardCons instance from a JSON dictionary.

        :param harness_connections: A list of dictionaries representing the harness connections
        :return: A DutBoardCons instance
        """
        parsed_connections: dict[DutCon, HilDutCon] = {}

        for con in harness_connections:
            match con:
                case {"dut": dut_con, "hil": hil_con}:
                    parsed_connections[DutCon.from_json(dut_con)] = HilDutCon.from_json(
                        hil_con
                    )
                case _:
                    error_msg = f"Invalid DUT board connection configuration: {con}"
                    raise hil_errors.ConfigurationError(error_msg)

        return cls(parsed_connections)

    def get_hil_device_connection(self, dut_con: DutCon) -> HilDutCon:
        """
        Get the HIL device connection for a given DUT connection.

        :param dut_con: The DUT connection for which to retrieve the HIL device connection
        :return: The corresponding HIL device connection
        """
        if dut_con in self._harness_connections:
            return self._harness_connections[dut_con]
        else:
            error_msg = (
                "No HIL connection found for DUT connection: "
                f"({dut_con.connector}, {dut_con.pin})"
            )
            raise hil_errors.ConnectionError(error_msg)


# All DUT Connections -----------------------------------------------------------------#
class DutCons:
    def __init__(self, dut_connections: dict[str, DutBoardCons]):
        """
        :param dut_connections: A dictionary mapping DUT board names to their connections
        """
        self._dut_connections: dict[str, DutBoardCons] = dut_connections

    @classmethod
    def from_json(cls, test_config_path: str) -> "DutCons":
        """
        Create a DutCons instance from a JSON configuration file.

        :param test_config_path: The path to the JSON configuration file
        :return: A DutCons instance
        """
        with open(test_config_path, "r") as test_config_file:
            test_config = json.load(test_config_file)

        board_cons = {}
        match test_config:
            case {"dut_connections": dut_connections}:
                for board_cons in dut_connections:
                    ...
                    match board_cons:
                        case {
                            "board": board,
                            "harness_connections": harness_connections,
                        }:
                            board_cons[board] = DutBoardCons.from_json(
                                harness_connections
                            )
                        case _:
                            error_msg = (
                                "Invalid DUT connections configuration: "
                                f"{board_cons}"
                            )
                            raise hil_errors.ConfigurationError(error_msg)
            case _:
                # Not an error to have no DUT connections
                pass

        return cls(board_cons)

    def get_hil_device_connection(self, board: str, dut_con: DutCon) -> HilDutCon:
        """
        Get the HIL device connection for a given DUT connection.

        :param board: The name of the DUT board
        :param dut_con: The DUT connection for which to retrieve the HIL device connection
        :return: The corresponding HIL device connection
        """
        if board in self._dut_connections:
            return self._dut_connections[board].get_hil_device_connection(dut_con)
        else:
            error_msg = f"No HIL connection found for DUT board: {board}"
            raise hil_errors.ConnectionError(error_msg)
